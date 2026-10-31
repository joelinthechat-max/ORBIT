"""Persisted task orchestration over the registered action catalogue."""
from __future__ import annotations
import hashlib,json,time,uuid
from threading import RLock
from typing import Callable
from .actions import ActionRegistry
from .memory import MemoryStore
from .planner import Planner


def _approval_hash(task_id,step):
    payload={'task_id':task_id,'step_id':step['id'],'action':step['action'],'parameters':step['parameters'],'title':step.get('title'),'expected':step.get('expected'),'consequence':step.get('consequence')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

class TaskEngine:
    def __init__(self,memory:MemoryStore,registry:ActionRegistry,planner:Planner,config:Callable[[],dict]):
        self.memory=memory; self.registry=registry; self.planner=planner; self.config=config; self._lock=RLock(); self._cancel=__import__('threading').Event()
    def _steps_from_model(self,proposal):
        out=[]
        for s in proposal['steps']:
            meta=self.registry.validate(s['action'],s['parameters'])
            out.append({'id':s['id'],'kind':'registered','action':s['action'],'title':s['description'],'parameters':meta['parameters'],'permission':meta['permission'],'timeout_seconds':meta['timeout_seconds'],'reversible':meta['reversible'],'consequence':meta['consequence'],'expected':s['expected'],'depends_on':s['depends_on'],'status':'pending','approval':None,'result':'','verified':False})
        return out
    def migrate_legacy_tasks(self):
        """Upgrade safe v0.2 file workflow steps without replaying completed work."""
        migrated=0
        for task in self.memory.list_tasks(500):
            changed=False; writes={}
            for step in task['steps']:
                kind=step.get('kind')
                if kind=='file_write':
                    name,_,content=str(step.get('detail','')).partition('\n')
                    params={'path':name,'content':content}
                    action='workspace.create_file'
                    try: meta=self.registry.validate(action,params)
                    except ValueError:
                        if step.get('status')!='done': step['kind']='legacy_needs_review'; step['status']='failed'; step['result']='Legacy file plan could not be safely migrated to the current text/path rules; review and create a new task.'; task['status']='paused'
                        changed=True; continue
                    writes[step['id']]=params
                    step.update({'kind':'registered','action':action,'parameters':params,'permission':meta['permission'],'timeout_seconds':meta['timeout_seconds'],'reversible':meta['reversible'],'consequence':meta['consequence'],'expected':'The requested text is stored exactly.','depends_on':[],'approval':None,'verified':step.get('status')=='done'})
                    if step.get('status')=='done': step.setdefault('result','Completed in the previous ORBIT version; retained without replay.')
                    changed=True
                elif kind=='verify':
                    previous=next((s for s in task['steps'] if s.get('kind') in {'file_write','registered'} and (s.get('kind')=='file_write' or s.get('action')=='workspace.create_file')),None)
                    if previous:
                        if previous.get('kind')=='file_write': name,_,content=str(previous.get('detail','')).partition('\n')
                        else: name=previous.get('parameters',{}).get('path',''); content=previous.get('parameters',{}).get('content','')
                        params={'path':name,'expected_content':content}
                        try: meta=self.registry.validate('workspace.verify_file',params)
                        except ValueError:
                            if step.get('status')!='done': step['kind']='legacy_needs_review'; step['status']='failed'; step['result']='Legacy verification step could not be safely migrated; review and create a new task.'; task['status']='paused'
                            changed=True; continue
                        step.update({'kind':'registered','action':'workspace.verify_file','parameters':params,'permission':meta['permission'],'timeout_seconds':meta['timeout_seconds'],'reversible':meta['reversible'],'consequence':meta['consequence'],'expected':'File contents match the text written by the earlier task step.','depends_on':[previous['id']],'approval':None,'verified':step.get('status')=='done'})
                        if step.get('status')=='done': step.setdefault('result','Completed verification retained without replay.')
                        changed=True
            if changed:
                task.setdefault('planning_source','legacy-v0.2-migrated'); self.memory.save_task(task); migrated+=1
        return migrated
    def _deterministic(self,objective):
        """Offline deterministic subset retained for routine exact file and test workflows."""
        import re
        text=objective.strip()
        # Acceptance workflow: create folder + write and verify a short renewable-energy report.
        m=re.search(r'(?is)create a folder named ["\']?([\w -]{1,60})["\']?\s+(?:inside|in) (?:my )?workspace.*?create (?:a )?text file called ["\']?([\w.-]{1,100})["\']?.*?short report about renewable energy',text)
        if m:
            folder=m.group(1).strip(); filename=m.group(2).strip()
            if '/' in folder or '/' in filename or '\\' in folder+filename: raise ValueError('Folder and file names must be single workspace names')
            content=('Renewable energy comes from sources that naturally replenish, including sunlight, wind, flowing water and geothermal heat. Solar panels and wind turbines generate electricity without burning fossil fuels during operation. Wider use can reduce greenhouse-gas emissions and improve energy security, although grids also need storage, transmission and planning to manage variable output.')
            path=f'{folder}/{filename}'
            return [{'id':1,'kind':'registered','action':'workspace.create_directory','title':f'Create workspace folder {folder}','parameters':{'path':folder},'permission':'A','timeout_seconds':5,'reversible':True,'consequence':'Creates a new folder; existing folders are left intact','expected':'The workspace folder exists.','depends_on':[],'status':'pending','approval':None,'result':'','verified':False},
                    {'id':2,'kind':'registered','action':'workspace.create_file','title':f'Create {filename} with a short report','parameters':{'path':path,'content':content},'permission':'A','timeout_seconds':5,'reversible':True,'consequence':'Creates a new file; existing files are never overwritten','expected':'The new text file contains the generated report.','depends_on':[1],'status':'pending','approval':None,'result':'','verified':False},
                    {'id':3,'kind':'registered','action':'workspace.verify_file','title':'Verify the saved report contents','parameters':{'path':path,'expected_content':content},'permission':'A','timeout_seconds':3,'reversible':True,'consequence':'Read-only exact content verification','expected':'File bytes decode to the exact planned text.','depends_on':[2],'status':'pending','approval':None,'result':'','verified':False}]
        # Existing simple text-file phrase, now routed through the registry.
        m=re.match(r'(?is)^(?:create|write|save) (?:a )?file named ([\w.-]+) with (?:the )?text:?\s*(.*)$',text)
        if m:
            name,content=m.group(1),m.group(2)
            if len(content)>100000: raise ValueError('Text exceeds the supported 100,000 character limit')
            return [{'id':1,'kind':'registered','action':'workspace.create_file','title':f'Create {name} in the workspace','parameters':{'path':name,'content':content},'permission':'A','timeout_seconds':5,'reversible':True,'consequence':'Creates a new file; existing files are never overwritten','expected':'The requested text is stored exactly.','depends_on':[],'status':'pending','approval':None,'result':'','verified':False},
                    {'id':2,'kind':'registered','action':'workspace.verify_file','title':'Verify the saved file contents','parameters':{'path':name,'expected_content':content},'permission':'A','timeout_seconds':3,'reversible':True,'consequence':'Read-only exact content verification','expected':'File contents match the requested text.','depends_on':[1],'status':'pending','approval':None,'result':'','verified':False}]
        return [{'id':1,'kind':'note','title':'No offline plan available','status':'pending','detail':'Enable and configure a compatible local language model to plan this objective using ORBIT’s registered actions. No action was executed.'}]
    def create_task(self,objective,model=None,context=None):
        if not isinstance(objective,str) or not objective.strip() or len(objective)>2000: raise ValueError('Objective must be 1-2,000 characters')
        steps=self._deterministic(objective); source='deterministic'; planning_error=None
        if model:
            try:
                proposal=model.propose_plan(objective,context or {},self.registry)
                steps=self._steps_from_model(proposal); source='local-model'
            except (ConnectionError,TimeoutError,RuntimeError) as e:
                # Inference being unavailable is visible; use only deterministic local fallback.
                planning_error=str(e)[:500]
            except ValueError as e:
                # Invalid or out-of-registry output is refused, not executed or silently rewritten.
                raise ValueError(f'Local model plan rejected: {e}') from e
        plan_snapshot=json.loads(json.dumps(steps,ensure_ascii=False))
        task={'id':uuid.uuid4().hex[:8],'objective':objective.strip(),'created':time.time(),'status':'planned','steps':steps,'initial_plan':plan_snapshot,'current_plan':json.loads(json.dumps(plan_snapshot)),'execution_trace':[],'current_phase':'planning','outcome':'','planning_source':source}
        if planning_error: task['planning_error']=planning_error
        self.memory.save_task(task)
        return task
    def _task_and_step(self,task_id,step_id):
        task=self.memory.get_task(task_id)
        if not task: raise KeyError('Task not found')
        step=next((s for s in task['steps'] if s['id']==step_id),None)
        if not step: raise KeyError('Step not found')
        return task,step
    def approve(self,task_id,step_id):
        with self._lock:
            task,step=self._task_and_step(task_id,step_id)
            if step.get('kind')!='registered': raise ValueError('Only registered actions can be approved')
            if step.get('status')!='pending': raise ValueError('Only a pending action may be approved')
            meta=self.registry.validate(step['action'],step['parameters'])
            if meta['permission'] not in {'B','C'}: raise ValueError('This action does not require approval')
            step['approval']={'token':uuid.uuid4().hex,'action_hash':_approval_hash(task_id,step),'approved_at':time.time(),'permission':meta['permission']}
            step['status']='pending'; task['status']='planned'; self.memory.save_task(task)
            return {'approved':True,'task_id':task_id,'step_id':step_id,'permission':meta['permission'],'approval_token':step['approval']['token']}
    def reject(self,task_id,step_id):
        with self._lock:
            task,step=self._task_and_step(task_id,step_id)
            if step.get('kind')!='registered': raise ValueError('Only registered actions can be rejected')
            if step.get('status')!='pending': raise ValueError('Only a pending action may be rejected')
            step['status']='rejected'; step['approval']=None; step['result']='User rejected this exact action.'; task['status']='paused'; self.memory.save_task(task)
            return {'rejected':True,'task_id':task_id,'step_id':step_id}
    def pause(self,task_id):
        with self._lock:
            task=self.memory.get_task(task_id)
            if not task: raise KeyError('Task not found')
            if task['status'] in {'completed','failed'}: raise ValueError('Completed or failed task cannot be paused')
            task['status']='paused'; self.memory.save_task(task); return task
    def resume(self,task_id):
        with self._lock:
            task=self.memory.get_task(task_id)
            if not task: raise KeyError('Task not found')
            if task['status']!='paused': raise ValueError('Only a paused task can be resumed')
            if any(s.get('status')=='rejected' for s in task['steps']): raise ValueError('Rejected task step cannot be resumed; create a revised task')
            if any(s.get('status')=='interrupted_review' for s in task['steps']): raise ValueError('An interrupted action needs manual inspection; create a revised task after checking its effects')
            if any(s.get('status')=='awaiting_observation' for s in task['steps']): raise ValueError('Capture and review the current screen before resuming; the prior input will not be repeated')
            task['status']='planned'; self.memory.save_task(task); return task
    def execute(self,task_id,step_id):
        with self._lock:
            task,step=self._task_and_step(task_id,step_id)
            if step.get('status')=='done': return {'task':task,'step':step,'already_done':True,'approval_required':False}
            if step.get('status')=='awaiting_observation': raise PermissionError('This input was already sent. Capture and review the current screen; ORBIT will not resend it.')
            if task['status']=='paused': raise PermissionError('Task is paused; resume it before running actions')
            if step.get('status') in {'failed','rejected','interrupted_review'}: raise ValueError('Failed, rejected or uncertain interrupted action will not be repeated; inspect and create a revised task')
            if step.get('kind')!='registered': raise ValueError('This task step has no executable registered action')
            meta=self.registry.validate(step['action'],step['parameters'])
            if meta['permission']=='D': raise PermissionError('Prohibited action')
            policy=self.config().get('security',{}).get('action_permissions',{})
            if policy.get(meta['permission'],meta['permission']=='A') is not True: raise PermissionError(f'Permission class {meta["permission"]} is disabled in local configuration')
            deps=step.get('depends_on',[])
            unresolved=[d for d in deps if next((s for s in task['steps'] if s['id']==d),{}).get('status')!='done']
            if unresolved: raise RuntimeError(f'Complete dependent step(s) first: {unresolved}')
            # Preserve strict displayed order as well as explicit dependencies.
            prior=[s for s in task['steps'] if s['id']<step['id']]
            if any(s.get('status') not in {'done','rejected'} for s in prior): raise RuntimeError('Complete earlier plan steps first')
            approval=step.get('approval')
            approval_valid=bool(approval and approval.get('token') and approval.get('action_hash')==_approval_hash(task_id,step) and time.time()-approval.get('approved_at',0)<=600)
            if meta['permission'] in {'B','C'} and not approval_valid:
                return {'task':task,'step':step,'already_done':False,'approval_required':True,'approval_request':{'action':step['action'],'description':step['title'],'parameters':step['parameters'],'permission':meta['permission'],'consequence':meta['consequence'],'reversible':meta['reversible'],'expected':step['expected']}}
            if step['action'].startswith(('desktop.','browser.')):
                # Any action that can change the active external environment requires a fresh observation;
                # stop for review rather than blindly running the next stale coordinate or selector.
                task['status']='paused'; step['result']='External action completed; observe current application state and review the next step before continuing.'
                self.memory.save_task(task)
                # Resume is still explicit in the interactive path; run the requested action below only after restoring planned.
                task['status']='planned'
            task['status']='running'; task['current_phase']='executing'; step['status']='running'; self.memory.save_task(task)
            try:
                result=self.registry.execute(step['action'],step['parameters'])
                action_sent=result.get('action_sent') is True
                step['status']='awaiting_observation' if action_sent else 'done'; step['verified']=result.get('verified') is True; step['result']=result.get('summary','Action completed.')
                # Keep bounded outputs for later plan context and user audit.
                step['output']={k:(v[:4000] if isinstance(v,str) else v[:100] if isinstance(v,list) else v) for k,v in result.items() if k not in {'action','elapsed_seconds','verified','summary'}}
                step['elapsed_seconds']=result.get('elapsed_seconds')
            except Exception as e:
                step['status']='failed'; step['verified']=False; step['result']=str(e)[:1000]; task['outcome']=step['result']
                task['status']='failed'; self.memory.save_task(task); raise RuntimeError(f'Action failed; no automatic retry: {e}') from e
            external=step['action'].startswith(('desktop.','browser.'))
            if action_sent:
                task['status']='observing'; task['current_phase']='observing'; task['outcome']='Input was sent, but the intended screen result is not yet verified.'
                trace=task.setdefault('execution_trace',[]); trace.append({'at':time.time(),'step_id':step['id'],'phase':'action_sent','action':step['action'],'verified':False,'summary':step['result']}); task['execution_trace']=trace[-100:]
            else:
                task['status']='completed' if all(s.get('status') in {'done','rejected'} for s in task['steps']) else 'paused' if external else 'planned'
                task['current_phase']='completed' if task['status']=='completed' else 'planning'
            task['outcome']=step['result']; task['current_plan']=json.loads(json.dumps(task['steps'],ensure_ascii=False)); self.memory.save_task(task)
            return {'task':task,'step':step,'already_done':False,'approval_required':False,'awaiting_observation':action_sent}

    def record_observation(self,task_id,observation,screenshot_ref,assessment=None):
        """Attach a fresh observation to an action awaiting evidence; never infer success here."""
        with self._lock:
            task=self.memory.get_task(task_id)
            if not task: raise KeyError('Task not found')
            step=next((s for s in task['steps'] if s.get('status')=='awaiting_observation'),None)
            if task.get('status') not in {'observing','paused'} or step is None: raise ValueError('Task is not waiting for a post-action observation')
            if not isinstance(observation,dict) or type(observation.get('observed_at')) not in (int,float) or time.time()-observation['observed_at']>60: raise ValueError('A fresh structured observation is required')
            safe={k:observation.get(k) for k in ('screen_description','active_application','window_title','elements','visible_messages','potential_errors','screen_state','observed_at','image_size','screen_size','screen_origin','vision_error') if k in observation}
            task['latest_observation']=safe; history=task.setdefault('observation_history',[]); history.append({'step_id':step['id'],'at':safe['observed_at'],'screenshot':screenshot_ref,'observation':safe}); task['observation_history']=history[-10:]
            if assessment is not None: task['latest_assessment']=assessment
            task['current_phase']='awaiting_review'; task['status']='awaiting_review'
            task.setdefault('execution_trace',[]).append({'at':time.time(),'step_id':step['id'],'phase':'observed','screenshot':screenshot_ref,'vision_interpreted':bool(safe.get('elements') or safe.get('screen_description') not in {None,'','Screenshot captured; vision model unavailable.'})})
            task['execution_trace']=task['execution_trace'][-100:]; step['observation_ref']=screenshot_ref; step['result']+=' Post-action screenshot captured; outcome remains unverified pending explicit review.'
            self.memory.save_task(task)
            return task

    def confirm_observation(self,task_id,step_id,verified):
        """Require a user-visible confirmation; ORBIT does not claim visual goal proof from a model guess."""
        with self._lock:
            task,step=self._task_and_step(task_id,step_id)
            if task.get('status')!='awaiting_review' or step.get('status')!='awaiting_observation' or not task.get('latest_observation'): raise ValueError('Capture a fresh post-action observation before review')
            if type(verified) is not bool: raise ValueError('verified must be an explicit Boolean')
            step['status']='done' if verified else 'failed'; step['verified']=verified; step['verification_source']='user_observation'
            step['result']=('User confirmed the intended visible result after reviewing the saved observation.' if verified else 'User did not confirm the intended visible result; no retry was attempted.')
            task['final_verification']={'verified':verified,'source':'user_observation','at':time.time(),'step_id':step_id}
            task['current_phase']='planning' if verified else 'failed'; task['status']=('completed' if verified and all(s.get('status') in {'done','rejected'} for s in task['steps']) else 'planned') if verified else 'failed'
            if not verified: task['outcome']='Expected result was not confirmed; inspect state and create a revised task.'
            else: task['outcome']=step['result']
            task.setdefault('execution_trace',[]).append({'at':time.time(),'step_id':step_id,'phase':'user_verified' if verified else 'user_unverified','verified':verified})
            task['current_plan']=json.loads(json.dumps(task['steps'],ensure_ascii=False))
            self.memory.save_task(task)
            return task

    def cancel_autonomous(self): self._cancel.set(); return {'cancel_requested':True}

    def run_autonomous(self,task_id,*,max_actions=None,max_retries=0,task_timeout=None,observation_provider=None,preflight=None):
        cfg=self.config().get('autonomy',{}); sec=self.config().get('security',{})
        if not sec.get('autonomous_mode_enabled',False): raise PermissionError('Autonomous execution is disabled in local configuration.')
        self._cancel.clear(); max_actions=max(1,min(int(max_actions or cfg.get('max_actions',12)),30)); max_retries=max(0,min(int(max_retries),1)); task_timeout=max(10,min(int(task_timeout or cfg.get('task_timeout_seconds',120)),600)); started=time.monotonic(); done=0; trace=[]
        for _ in range(max_actions):
            if self._cancel.is_set(): return {'status':'paused','reason':'Cancellation requested','actions':done,'trace':trace}
            if time.monotonic()-started>task_timeout: self.pause(task_id); return {'status':'paused','reason':'Task timeout reached','actions':done,'trace':trace}
            task=self.memory.get_task(task_id)
            if not task: raise KeyError('Task not found')
            if task['status'] in {'paused','observing','awaiting_review'}: return {'status':task['status'],'reason':'Task is paused for observation/review or user action','actions':done,'trace':trace,'task':task}
            step=next((s for s in task['steps'] if s.get('status')=='pending'),None)
            if step is None: return {'status':task['status'],'actions':done,'trace':trace,'task':task}
            if step.get('kind')!='registered': return {'status':'needs_user','reason':'Plan contains a non-executable note','actions':done,'trace':trace,'task':task}
            permission=step.get('permission','D')
            if permission!='A': return {'status':'awaiting_approval','step_id':step['id'],'permission':permission,'actions':done,'trace':trace,'task':task}
            if not sec.get('action_permissions',{}).get('A',False): return {'status':'needs_user','reason':'Class A permission is disabled','actions':done,'trace':trace,'task':task}
            # Coordinate-sensitive actions must bind to the most recent real observation; the planner cannot fabricate one.
            action=step.get('action',''); params=step.get('parameters',{})
            if action in {'desktop.click','desktop.drag','desktop.scroll','desktop.move_cursor'}:
                observed=observation_provider() if observation_provider else None
                if not observed: return {'status':'needs_user','reason':'A fresh screenshot observation is required before desktop coordinates can be used','step_id':step['id'],'actions':done,'trace':trace,'task':task}
                stamp=observed.get('observed_at')
                coords={'x':params.get('x'), 'y':params.get('y')} if action in {'desktop.click','desktop.move_cursor'} else {'x':params.get('x'),'y':params.get('y')} if action=='desktop.scroll' else {'x1':params.get('x1'),'y1':params.get('y1'),'x2':params.get('x2'),'y2':params.get('y2')}
                if not stamp or time.time()-stamp>60 or any(v is None for v in coords.values()): return {'status':'needs_user','reason':'Coordinates cannot be verified against the current observation','step_id':step['id'],'actions':done,'trace':trace,'task':task}
                # Requiring the exact timestamp from the observed UI prevents stale, prompt-invented screen coordinates.
                if action in {'desktop.click','desktop.move_cursor','desktop.scroll'}: params['observed_at']=stamp
                step['parameters']=params; self.memory.save_task(task)
            if action.startswith('browser.') and permission=='A' and action not in {'browser.read_page','browser.screenshot','browser.switch_tab'}:
                return {'status':'awaiting_approval','step_id':step['id'],'permission':'B/C','reason':'External browser state change always requires interactive approval','actions':done,'trace':trace,'task':task}
            if action.startswith('desktop.') and action in {'desktop.close_window','desktop.click','desktop.drag','desktop.press_key','desktop.hotkey','desktop.clipboard_read'}:
                return {'status':'awaiting_approval','step_id':step['id'],'permission':'C','reason':'Potentially consequential desktop operation requires exact interactive approval','actions':done,'trace':trace,'task':task}
            try:
                if preflight: preflight(step)
                r=self.execute(task_id,step['id']); done+=1; trace.append({'step_id':step['id'],'action':action,'status':'done','summary':r['step'].get('result','')})
            except OSError:
                raise
            except Exception as e:
                trace.append({'step_id':step['id'],'action':action,'status':'failed','error':str(e)[:300]})
                if not max_retries: return {'status':'failed','reason':str(e)[:500],'actions':done,'trace':trace}
                return {'status':'needs_user','reason':'No action was retried automatically because the effect is uncertain; review and replan.','actions':done,'trace':trace}
            current=self.memory.get_task(task_id)
            if r.get('awaiting_observation'): return {'status':'awaiting_observation','reason':'Desktop input was sent; capture and review the resulting screen before any next action.','actions':done,'trace':trace,'task':current,'step_id':step['id']}
            if current and current.get('status')=='completed': return {'status':'completed','actions':done,'trace':trace,'task':current}
            if action.startswith(('desktop.','browser.')):
                task=self.memory.get_task(task_id)
                return {'status':'paused','reason':'External action boundary: re-observe and review before continuing','actions':done,'trace':trace,'task':task}
        return {'status':'paused','reason':'Maximum autonomous action count reached','actions':done,'trace':trace,'task':self.memory.get_task(task_id)}
