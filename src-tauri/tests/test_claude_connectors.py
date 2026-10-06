import importlib.util,json,unittest,os,sys,tempfile,subprocess
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'resources/claude_connectors.py'
spec=importlib.util.spec_from_file_location('connectors',p); c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
MAIL='mcp__claude_ai_Gmail__gmail_search_messages'
CAL='mcp__claude_ai_Google_Calendar__gcal_list_events'
CONFIG={'enabled':True,'gmail':True,'calendar':True,'gmail_query':'label:UAM newer_than:7d','calendar_ids':['primary'],'read_tools':[MAIL,CAL]}
def events(error=False):
    value={'status':'available','summary':'Resumen de prueba','error':'','items':[]}
    return [{'type':'assistant','message':{'content':[{'type':'tool_use','id':'x','name':MAIL}]}},
            {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'x','is_error':error,'content':'[]'}]}},
            {'type':'result','structured_output':{'mail':value,'calendar':value}}]
class ConnectorTests(unittest.TestCase):
    def test_only_concrete_reads_allowed(self):
        for name in [MAIL,CAL]:self.assertTrue(c.guard({'tool_name':name},[MAIL,CAL]))
        for name in ['Bash','Write','mcp__Gmail__gmail_send_message','mcp__Gmail__*','mcp__Calendar__create_event']:
            self.assertFalse(c.guard({'tool_name':name},[MAIL,CAL,name]))
    def test_scope_blocks_other_mail_and_calendars(self):
        self.assertTrue(c.guard({'tool_name':MAIL,'tool_input':{'query':CONFIG['gmail_query']}},[MAIL],CONFIG))
        self.assertFalse(c.guard({'tool_name':MAIL,'tool_input':{'query':'in:anywhere'}},[MAIL],CONFIG))
        self.assertFalse(c.guard({'tool_name':CAL,'tool_input':{'calendar_id':'not-chosen'}},[CAL],CONFIG))
        self.assertTrue(c.guard({'tool_name':CAL,'tool_input':{'calendar_id':'primary'}},[CAL],CONFIG))
    def test_current_claude_ai_connector_names(self):
        threads='mcp__claude_ai_Gmail__search_threads';events_='mcp__claude_ai_Google_Calendar__list_events';search='mcp__claude_ai_Google_Calendar__search_events'
        for name in [threads,'mcp__claude_ai_Gmail__get_thread','mcp__claude_ai_Gmail__list_labels']:self.assertEqual(c.source_for_tool(name),'mail')
        for name in ['mcp__claude_ai_Gmail__send_message','mcp__claude_ai_Gmail__create_draft','mcp__claude_ai_Gmail__label_thread','mcp__claude_ai_Google_Calendar__create_event']:self.assertIsNone(c.source_for_tool(name))
        self.assertTrue(c.guard({'tool_name':threads,'tool_input':{'query':CONFIG['gmail_query'],'pageSize':40}},[threads],CONFIG))
        self.assertFalse(c.guard({'tool_name':threads,'tool_input':{}},[threads],CONFIG))
        self.assertFalse(c.guard({'tool_name':threads,'tool_input':{'query':'in:anywhere'}},[threads],CONFIG))
        # calendarId omitido = primary
        self.assertTrue(c.guard({'tool_name':events_,'tool_input':{}},[events_],CONFIG))
        self.assertTrue(c.guard({'tool_name':events_,'tool_input':{'calendarId':'primary'}},[events_],CONFIG))
        self.assertFalse(c.guard({'tool_name':events_,'tool_input':{}},[events_],dict(CONFIG,calendar_ids=['otro@group.calendar.google.com'])))
        self.assertTrue(c.guard({'tool_name':search,'tool_input':{'query':'seminario'}},[search],CONFIG))
    def test_no_tool_call_never_means_empty_inbox(self):
        result=c.project_events(events()[2:],CONFIG)
        self.assertEqual(result['mail']['status'],'unavailable')
    def test_failed_tool_is_unavailable(self):
        self.assertEqual(c.project_events(events(True),CONFIG)['mail']['status'],'unavailable')
    def test_successful_empty_query_is_valid(self):
        result=c.project_events(events(),CONFIG)
        self.assertEqual(result['mail']['status'],'available')
        self.assertEqual(result['calendar']['status'],'unavailable')
    def test_failed_followup_degrades_coverage(self):
        e=events()+[{'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'x','is_error':True}]}}]
        self.assertEqual(c.project_events(e,CONFIG)['mail']['status'],'partial')
    def test_disabled_source_cannot_be_allowed(self):
        cfg=dict(CONFIG,calendar=False)
        self.assertEqual(c.allowed_tools(cfg),[MAIL])
        self.assertNotIn('calendar',c.project_events(events(),cfg))
    def test_ephemeral_and_no_local_tools(self):
        args=c.build_command('claude',CONFIG,'sonnet','high')
        self.assertIn('--no-session-persistence',args)
        self.assertEqual(args[args.index('--tools')+1],'ToolSearch')
        self.assertEqual(args[args.index('--permission-mode')+1],'dontAsk')
        settings=json.loads(args[args.index('--settings')+1]);self.assertIn('PreToolUse',settings['hooks'])
        self.assertNotIn('--dangerously-skip-permissions',args)
    def test_capture_waits_for_claude_ai_connectors(self):
        seen={}
        def fake(command,prompt,cwd,env,timeout=240):
            seen.update(env=env,prompt=prompt);return []
        original=c.run_bounded;c.run_bounded=fake
        try:c.capture({'modules':{'claude_connectors':CONFIG},'tools':{'claude':'claude'}},'sonnet','high','login')
        finally:c.run_bounded=original
        self.assertEqual(seen['env']['MCP_CONNECTION_NONBLOCKING'],'false')
        self.assertIn('select:',seen['prompt'])
    def test_hook_exec_form_has_no_shell(self):
        args=c.build_command('claude',CONFIG,'sonnet','high');settings=json.loads(args[args.index('--settings')+1])
        hook=settings['hooks']['PreToolUse'][0]['hooks'][0]
        self.assertEqual(hook['command'],sys.executable)
        self.assertEqual(hook['args'][-1],'guard')
        result=subprocess.run([hook['command'],*hook['args']],input=json.dumps({'tool_name':'Bash'}),text=True,capture_output=True,env=dict(os.environ,ESPRIT_CONNECTOR_TOOLS=json.dumps([MAIL]),ESPRIT_CONNECTOR_SCOPE=json.dumps(CONFIG)))
        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_bounded_process_uses_synthetic_data(self):
        with tempfile.TemporaryDirectory() as cwd:
            result=c.run_bounded([sys.executable,'-c','import json; print(json.dumps({"type":"result"}))'],'',cwd,os.environ,5)
            self.assertEqual(result,[{'type':'result'}])
            with self.assertRaises(subprocess.TimeoutExpired):
                c.run_bounded([sys.executable,'-c','import time; time.sleep(20)'],'',cwd,os.environ,.1)
    def test_oversized_summary_rejected(self):
        e=events();e[-1]['structured_output']['mail']['summary']='x'*12001
        self.assertEqual(c.project_events(e,CONFIG)['mail']['status'],'unavailable')
if __name__=='__main__':unittest.main()
