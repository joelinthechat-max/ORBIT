"""Best-effort local resource metrics. Missing measurements are returned as null, never fabricated."""
from __future__ import annotations
import os, re, time, ctypes

class ResourceMonitor:
    def __init__(self): self._last_cpu=None; self._last_at=None
    @staticmethod
    def _linux_meminfo():
        out={}
        try:
            with open('/proc/meminfo',encoding='ascii') as f:
                for line in f:
                    m=re.match(r'^(MemTotal|MemAvailable):\s+(\d+)\s+kB',line)
                    if m: out[m.group(1)]=int(m.group(2))*1024
        except OSError: pass
        return out
    @staticmethod
    def _linux_rss(pid=None):
        path=f'/proc/{pid}/status' if pid else '/proc/self/status'
        try:
            with open(path,encoding='ascii') as f:
                for line in f:
                    if line.startswith('VmRSS:'): return int(line.split()[1])*1024
        except (OSError,ValueError,IndexError): pass
        return None
    @staticmethod
    def _linux_cpu():
        try:
            with open('/proc/stat',encoding='ascii') as f: fields=f.readline().split()[1:]
            values=[int(x) for x in fields]; idle=values[3]+(values[4] if len(values)>4 else 0); total=sum(values)
            return total,idle
        except (OSError,ValueError): return None
    @staticmethod
    def _windows_memory():
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
        try:
            x=MEMORYSTATUSEX(); x.dwLength=ctypes.sizeof(x)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x)): return {'total':int(x.ullTotalPhys),'available':int(x.ullAvailPhys),'load_percent':int(x.dwMemoryLoad)}
        except Exception: pass
        return {}
    @staticmethod
    def _windows_rss(pid=None):
        """Return a process working set using pointer-sized Win32 handles."""
        try:
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            psapi = ctypes.WinDLL('psapi', use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

            handle = kernel32.GetCurrentProcess() if pid is None else kernel32.OpenProcess(0x0400 | 0x0010, False, int(pid))
            if not handle:
                return None
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            try:
                ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
                return int(counters.WorkingSetSize) if ok else None
            finally:
                if pid is not None:
                    kernel32.CloseHandle(handle)
        except Exception:
            return None
    def sample(self,model_pids=None):
        model_pids=list(model_pids or []); model_rss=[]
        if os.name=='nt':
            m=self._windows_memory(); process=self._windows_rss(); model_rss=[self._windows_rss(p) for p in model_pids]
            available=m.get('available'); total=m.get('total'); cpu=None; source='GlobalMemoryStatusEx/PSAPI'
        else:
            m=self._linux_meminfo(); available=m.get('MemAvailable'); total=m.get('MemTotal'); process=self._linux_rss(); model_rss=[self._linux_rss(p) for p in model_pids]; cpu=None; source='/proc/meminfo and /proc/*/status'
            now=self._linux_cpu(); stamp=time.monotonic()
            if now and self._last_cpu and self._last_at:
                dt=now[0]-self._last_cpu[0]; di=now[1]-self._last_cpu[1]
                if dt>0: cpu=max(0.0,min(100.0,100.0*(dt-di)/dt))
            self._last_cpu=now; self._last_at=stamp
        known=[x for x in model_rss if x is not None]
        return {'available_ram_mb':round(available/1048576,1) if available is not None else None,'total_ram_mb':round(total/1048576,1) if total is not None else None,'application_rss_mb':round(process/1048576,1) if process is not None else None,'application_memory_kind':'current resident set','model_server_rss_mb':round(sum(known)/1048576,1) if known else None,'model_server_pids':len(model_pids),'cpu_percent':round(cpu,1) if cpu is not None else None,'cpu_kind':'system-wide delta sample' if cpu is not None else 'not yet measurable','source':source,'sampled_at':time.time(),'note':'Model RSS is null unless ORBIT owns/was given a model-server PID; all unavailable measures remain null.'}
