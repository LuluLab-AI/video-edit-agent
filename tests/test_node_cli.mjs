import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { LuluLabClient } from '../scripts/lululab_cli.mjs';

const json = value => new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } });
test('credits, workflow submit and task fetch preserve API contract', async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url: String(url), ...options });
    if (String(url).includes('/credits')) return json({total:1,items:[{creditsBalance:'7'}]});
    if (String(url).endsWith('/tasks') && options.method === 'POST') return json({id:'task-1'});
    return json({id:'task-1',status:'succeeded',output:{variants:[]}});
  };
  const client = new LuluLabClient({apiKey:'secret',baseUrl:'http://localhost',fetchImpl});
  assert.deepEqual(await client.credits(),{balance:7});
  assert.deepEqual(await client.submit('VideoEditingPolicyV1',{schemaVersion:1,operation:'plan_edit'}),{id:'task-1'});
  assert.equal((await client.task('task-1')).status,'succeeded');
  assert.deepEqual(JSON.parse(calls[1].body),{workflowId:'VideoEditingPolicyV1',input:{schemaVersion:1,operation:'plan_edit'}});
  assert.equal(calls[1].headers.Authorization,'secret');
});
test('upload and download work with Unicode paths', async () => {
  const dir=await mkdtemp(join(tmpdir(),'editor-node-'));
  const source=join(dir,'素材.mp4'), output=join(dir,'成片.mp4');
  await writeFile(source,Buffer.from('media'));
  const fetchImpl=async (url,options) => {
    if (String(url).endsWith('/uploads')) return json({presignedUrl:'https://storage.example/upload',location:'https://storage.example/media',mimeType:'video/mp4'});
    if (String(url).endsWith('/upload')) return new Response('',{status:200});
    if (String(url).endsWith('/video')) return new Response(Buffer.from('result'),{status:200});
    throw new Error('unexpected');
  };
  const client=new LuluLabClient({apiKey:'secret',baseUrl:'http://localhost',fetchImpl});
  assert.equal((await client.upload(source)).url,'https://storage.example/media');
  await client.download('https://storage.example/video',output);
  assert.equal((await readFile(output)).toString(),'result');
});
test('uncertain paid submission is not retried by client', async () => {
  let count=0;
  const client=new LuluLabClient({apiKey:'secret',baseUrl:'http://localhost',fetchImpl:async()=>{count++;throw Error('timeout')}});
  await assert.rejects(client.submit('VideoEditingPolicyV1',{schemaVersion:1}),/do not resubmit/);
  assert.equal(count,1);
});
