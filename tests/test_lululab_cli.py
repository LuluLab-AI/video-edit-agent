from pathlib import Path
import json, os, sys, tempfile, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import lululab_task as task
from language_context import resolve_context, save_context

class LanguageTests(unittest.TestCase):
    def test_priority_and_media_separation(self):
        cases=[('zh-CN','en-US','zh-CN'),('en-US','zh-CN','en-US'),('pt-BR','en-US','pt-BR'),('es-ES','en-US','es-ES')]
        for message,agent,expected in cases:
            self.assertEqual(resolve_context(message_locale=message,agent_default_locale=agent)['interactionLocale'],expected)
        self.assertEqual(resolve_context(agent_default_locale='en-US')['interactionLocale'],'en-US')
        self.assertEqual(resolve_context(agent_default_locale='zh-CN')['interactionLocale'],'zh-CN')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'language.json'
            save_context(path,message_locale='en-US',media_language='zh-CN')
            self.assertEqual(save_context(path)['interactionLocale'],'en-US')
            self.assertEqual(save_context(path,explicit_locale='ja-JP')['interactionLocale'],'ja-JP')
            self.assertEqual(save_context(path)['mediaLanguage'],'zh-CN')
        self.assertEqual(resolve_context(message_locale='zh-CN',media_language='en-US')['mediaLanguage'],'en-US')
        self.assertEqual(resolve_context()['interactionLocale'],'en')

class CliAdapterTests(unittest.TestCase):
    def test_bundled_node_entry_and_no_native_fallback(self):
        self.assertEqual(task.find_cli(),(ROOT/'scripts/lululab_cli.mjs').resolve())
        with self.assertRaisesRegex(RuntimeError,'NODE_CLI_MISSING'): task.find_cli('/bad/lululab.exe')
    def test_key_priority(self):
        with patch.dict(os.environ,{'LULULAB_API_KEY':'new','LZSTUDIO_API_KEY':'old'},clear=True):
            self.assertEqual(task.resolve_api_key(config_paths=[])[0],'new')
    def test_workflow_resume_without_resubmit(self):
        payload={'schemaVersion':1,'operation':'plan_edit'}
        expected={'operation':'plan_edit','variants':[{'id':'test'}]}
        with tempfile.TemporaryDirectory() as d, patch.object(task,'api_key',return_value='secret'), patch.object(task,'_run_cli',side_effect=[{'id':'t1'},{'status':'pending'},{'status':'succeeded','output':json.dumps(expected)}]) as call:
            state=Path(d)/'state.json'
            with patch.object(task.time,'monotonic',side_effect=[0,10]):
                with self.assertRaises(TimeoutError): task.submit_and_wait(payload,workflow_id='VideoEditingPolicyV1',timeout_seconds=5,state_path=state)
            self.assertEqual(task.submit_and_wait(payload,workflow_id='VideoEditingPolicyV1',state_path=state),expected)
            self.assertEqual([x.args[1][:2] for x in call.call_args_list],[['task','submit'],['task','fetch'],['task','fetch']])
            self.assertEqual(call.call_args_list[0].args[1][2:4],['--workflow-id','VideoEditingPolicyV1'])
    def test_secret_in_environment_not_argv(self):
        from types import SimpleNamespace
        seen={}
        def run(argv,**kwargs):
            seen.update(argv=argv,env=kwargs['env'])
            return SimpleNamespace(returncode=0,stdout='{"balance":2}',stderr='')
        with patch.object(task,'find_node',return_value='node'),patch.object(task.subprocess,'run',side_effect=run):
            self.assertEqual(task._run_cli(ROOT/'scripts/lululab_cli.mjs',['user','--credits'],key='secret'),{'balance':2})
        self.assertNotIn('secret',seen['argv'])
        self.assertEqual(seen['env']['LULULAB_API_KEY'],'secret')
    def test_upload_download_arguments(self):
        with patch.object(task,'api_key',return_value='secret'),patch.object(task,'_run_cli',return_value={'ok':True}) as call:
            task.upload_file(Path('C:/素材/视频.mp4'))
            self.assertEqual(call.call_args.args[1],['upload','C:/素材/视频.mp4'])
            task.download_result('https://example.org/video.mp4',Path('C:/输出/成片.mp4'))
            self.assertEqual(call.call_args.args[1],['download','--url','https://example.org/video.mp4','--output','C:/输出/成片.mp4'])
class CliIntegrationTests(unittest.TestCase):
    def test_python_node_mock_http_integration(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def respond(self, data):
                body=json.dumps(data).encode()
                self.send_response(200); self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                if self.path.startswith('/credits'): self.respond({'total':1,'items':[{'creditsBalance':'5'}]})
                elif self.path=='/tasks/task-1': self.respond({'id':'task-1','status':'succeeded','output':{'operation':'plan_edit','variants':[{'variant_id':'v1'}]}})
                elif self.path=='/result':
                    self.send_response(200); self.end_headers(); self.wfile.write(b'video')
            def do_POST(self):
                if self.path=='/tasks':
                    size=int(self.headers['Content-Length']); calls.append(json.loads(self.rfile.read(size)))
                    self.respond({'id':'task-1'})
                elif self.path=='/uploads':
                    host=f'http://127.0.0.1:{self.server.server_port}'
                    self.respond({'presignedUrl':host+'/signed','location':host+'/media','mimeType':'video/mp4'})
            def do_PUT(self):
                size=int(self.headers['Content-Length']); calls.append({'upload':self.rfile.read(size)})
                self.send_response(200); self.end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{
                'LULULAB_API_BASE_URL':f'http://127.0.0.1:{server.server_port}',
                'LULULAB_API_KEY':'mock-key'},clear=False):
                self.assertEqual(task.validate_api_key()['balance'],5)
                source=Path(d)/'素材.mp4'; source.write_bytes(b'media')
                self.assertTrue(task.upload_file(source)['url'].endswith('/media'))
                payload={'schemaVersion':1,'operation':'plan_edit'}
                result=task.submit_and_wait(payload,workflow_id='VideoEditingPolicyV1',state_path=Path(d)/'state.json')
                self.assertEqual(result['variants'][0]['variant_id'],'v1')
                self.assertEqual(calls[1],{'workflowId':'VideoEditingPolicyV1','input':payload})
                output=Path(d)/'成片.mp4'
                task.download_result(f'http://127.0.0.1:{server.server_port}/result',output)
                self.assertEqual(output.read_bytes(),b'video')
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

if __name__=='__main__': unittest.main()
