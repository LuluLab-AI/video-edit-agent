#!/usr/bin/env node
/** LuluLab API v1 client. Node.js >=20; no external packages. */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { basename, dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

export class LuluLabError extends Error {}

// Media metadata is distinct from the Content-Type required by a signed upload.
// Inspect bytes rather than trusting an extension or a generic storage MIME type.
export function imageMimeType(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])))
    return 'image/png';
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff)
    return 'image/jpeg';
  if (bytes.length >= 6 && ['GIF87a', 'GIF89a'].includes(bytes.toString('ascii', 0, 6)))
    return 'image/gif';
  if (bytes.length >= 12 && bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP')
    return 'image/webp';
  return null;
}

export const HELP = `LuluLab Node.js CLI (Node >=20)
  node lululab_cli.mjs upload <file>
  node lululab_cli.mjs task submit --workflow-id <id> --input <JSON>
  node lululab_cli.mjs task submit --workflow-id <id> --input-file <JSON file>
  node lululab_cli.mjs task fetch --id <id>
  node lululab_cli.mjs download --url <result URL> --output <file>
  node lululab_cli.mjs user --credits
Credentials: LULULAB_API_KEY (legacy LINGZHI_API_KEY / LZSTUDIO_API_KEY or
~/.ugc-product-video/config.json). Never pass credentials in command arguments.
Optional: LULULAB_API_BASE_URL (default https://customer.lululab.ai).
`;

export async function resolveApiKey(env = process.env, home = homedir()) {
  for (const name of ['LULULAB_API_KEY', 'LINGZHI_API_KEY', 'LZSTUDIO_API_KEY']) {
    if (env[name]?.trim()) return env[name].trim();
  }
  let config;
  try { config = JSON.parse(await readFile(join(home, '.ugc-product-video', 'config.json'), 'utf8')); }
  catch (error) {
    if (error.code !== 'ENOENT') throw new LuluLabError('CREDENTIAL_CONFIG_UNREADABLE');
  }
  if (typeof config?.apiKey === 'string' && config.apiKey.trim()) return config.apiKey.trim();
  throw new LuluLabError('API_KEY_REQUIRED: set LULULAB_API_KEY');
}

function webUrl(value, label) {
  let url;
  try { url = new URL(value); } catch { throw new LuluLabError(`${label}  is missing a valid URL`); }
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password)
    throw new LuluLabError(`${label} URL is invalid`);
  // HTTP is supported solely for local development and mock testing.
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))
    throw new LuluLabError(`${label}  requires HTTPS`);
  return url;
}

export class LuluLabClient {
  constructor({ apiKey, baseUrl = 'https://customer.lululab.ai', fetchImpl = globalThis.fetch,
                timeoutMs = 120000 } = {}) {
    this.base = webUrl(baseUrl, 'API');
    if (this.base.search || this.base.hash || !['', '/'].includes(this.base.pathname))
      throw new LuluLabError('API_BASE_INVALID: use a service root URL');
    if (!apiKey?.trim()) throw new LuluLabError('API_KEY_REQUIRED');
    this.key = apiKey.trim();
    this.fetch = fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  async request(path, { method = 'GET', body } = {}) {
    let response;
    try {
      response = await this.fetch(new URL(path, this.base), {
        method, headers: { Authorization: this.key, Accept: 'application/json',
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        redirect: 'error', signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch {
      throw new LuluLabError(method === 'POST' && path === '/tasks'
        ? 'SUBMISSION_UNCERTAIN: task may exist; do not resubmit'
        : 'API_NETWORK_OR_TIMEOUT');
    }
    // Do not print server response text, which could contain private data.
    if (!response.ok) throw new LuluLabError(`LuluLab API HTTP ${response.status} ${path === '/tasks' && method === 'POST' ? ' Do not resubmit.' : ''}`);
    try { return await response.json(); }
    catch { throw new LuluLabError('API_INVALID_JSON: do not resubmit a task'); }
  }

  async upload(file) {
    const bytes = await readFile(file);
    if (!bytes.length) throw new LuluLabError('UPLOAD_EMPTY_FILE');
    const actualMimeType = imageMimeType(bytes);
    const destination = await this.request('/uploads', { method: 'POST' });
    const presigned = webUrl(destination.presignedUrl, 'upload');
    const location = webUrl(destination.location, 'media');
    if (typeof destination.mimeType !== 'string' || !destination.mimeType.trim())
      throw new LuluLabError('UPLOAD_MIME_MISSING');
    const send = method => this.fetch(presigned, { method, body: bytes,
      headers: { 'Content-Type': destination.mimeType }, redirect: 'error',
      signal: AbortSignal.timeout(this.timeoutMs) });
    let response;
    try {
      const method = String(destination.method || destination.httpMethod || 'PUT').toUpperCase();
      if (!['PUT', 'POST'].includes(method)) throw new LuluLabError('UPLOAD_METHOD_UNSUPPORTED');
      response = await send(method);
      if (method === 'PUT' && response.status === 405 &&
          /(?:^|,|\s)POST(?:$|,|\s)/i.test(response.headers.get('allow') || '')) {
        response = await send('POST');
      }
    } catch (error) {
      if (error instanceof LuluLabError) throw error;
      throw new LuluLabError('UPLOAD_NETWORK_OR_TIMEOUT');
    }
    if (response.status === 415 && response.headers.get('allow') !== 'PUT') {
      const form = new FormData();
      form.append('file', new Blob([bytes], { type: destination.mimeType }), basename(file));
      try {
        response = await this.fetch(presigned, { method: 'POST', body: form,
          redirect: 'error', signal: AbortSignal.timeout(this.timeoutMs) });
      } catch { throw new LuluLabError('UPLOAD_NETWORK_OR_TIMEOUT'); }
    }
    if (!response.ok) throw new LuluLabError(`UPLOAD_HTTP_${response.status} (${presigned.hostname}; Allow ${response.headers.get('allow') || 'none'})`);
    // expiresAt describes the upload URL expiry, not the stored media lifetime.
    return { url: location.href, mimeType: actualMimeType || destination.mimeType };
  }

  async submit(workflowId, input) {
    if (typeof workflowId !== 'string' || !workflowId.trim()) throw new LuluLabError('WORKFLOW_ID_REQUIRED');
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new LuluLabError('TASK_INPUT_INVALID');
    const result = await this.request('/tasks', { method: 'POST', body: { workflowId, input } });
    if (typeof result?.id !== 'string' || !result.id.trim())
      throw new LuluLabError('SUBMISSION_UNCERTAIN: no task ID; do not resubmit');
    return result;
  }

  async task(id) {
    if (typeof id !== 'string' || !id.trim()) throw new LuluLabError('TASK_ID_REQUIRED');
    return this.request(`/tasks/${encodeURIComponent(id.trim())}`);
  }

  async credits() {
    let page = 1, seen = 0, balance = 0n;
    for (;;) {
      const result = await this.request(`/credits?page=${page}&pageSize=100`);
      const total = Number(result.total);
      if (!Number.isSafeInteger(total) || total < 0 || !Array.isArray(result.items))
        throw new LuluLabError('CREDITS_PAGINATION_INVALID');
      for (const account of result.items) {
        const raw = account.creditsBalance;
        if ((typeof raw !== 'string' && typeof raw !== 'number') ||
            !/^-?(0|[1-9]\d*)$/.test(String(raw)) ||
            (typeof raw === 'number' && !Number.isSafeInteger(raw)))
          throw new LuluLabError('CREDITS_BALANCE_INVALID');
        balance += BigInt(raw);
      }
      seen += result.items.length;
      if (seen >= total) break;
      if (!result.items.length || page >= 10000) throw new LuluLabError('CREDITS_PAGINATION_INCOMPLETE');
      page++;
    }
    if (balance > BigInt(Number.MAX_SAFE_INTEGER) || balance < BigInt(Number.MIN_SAFE_INTEGER))
      throw new LuluLabError('CREDITS_BALANCE_OUT_OF_RANGE');
    return { balance: Number(balance) };
  }

  async download(url, output) {
    const target = webUrl(url, 'result');
    let response;
    try { response = await this.fetch(target, { redirect: 'error', signal: AbortSignal.timeout(this.timeoutMs) }); }
    catch { throw new LuluLabError('Result download network error or timeout.'); }
    if (!response.ok) throw new LuluLabError(`Result download HTTP ${response.status}.`);
    await mkdir(dirname(output), { recursive: true });
    await writeFile(output, Buffer.from(await response.arrayBuffer()));
    return { output };
  }
}

export async function main(args = process.argv.slice(2)) {
  if (Number(process.versions.node.split('.')[0]) < 20) throw new LuluLabError('NODE_VERSION_UNSUPPORTED: install Node.js 20 or newer');
  if (args.includes('--help') || !args.length) {
    process.stdout.write(HELP); return;
  }
  const option = name => {
    const index = args.indexOf(name);
    if (index < 0 || !args[index + 1]) throw new LuluLabError(`Missing ${name}`);
    return args[index + 1];
  };
  // Validate commands before reading credentials or accessing the network.
  let action;
  if (args[0] === 'upload' && args.length === 2) action = client => client.upload(args[1]);
  else if (args[0] === 'user' && args.length === 2 && args[1] === '--credits') action = client => client.credits();
  else if (args[0] === 'task' && args[1] === 'fetch') {
    const id = option('--id'); action = client => client.task(id);
  } else if (args[0] === 'task' && args[1] === 'submit') {
    const workflow = option('--workflow-id');
    let input;
    if (args.includes('--input') === args.includes('--input-file')) throw new LuluLabError('Specify exactly one of --input or --input-file.');
    try { input = JSON.parse(args.includes('--input-file') ? await readFile(option('--input-file'), 'utf8') : option('--input')); }
    catch { throw new LuluLabError('Task input must be valid JSON.'); }
    action = client => client.submit(workflow, input);
  } else if (args[0] === 'download') {
    const url = option('--url'), output = option('--output');
    action = client => client.download(url, output);
  } else throw new LuluLabError('UNKNOWN_COMMAND: use --help');
  if (args.includes('--api-key')) throw new LuluLabError('Set credentials through the local environment');
  const client = new LuluLabClient({ apiKey: await resolveApiKey(),
    baseUrl: process.env.LULULAB_API_BASE_URL || 'https://customer.lululab.ai' });
  process.stdout.write(`${JSON.stringify(await action(client))}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    // Error messages are controlled by this module; filesystem errors can include paths.
    process.stderr.write(JSON.stringify({ ok: false, error: error instanceof LuluLabError ? error.message : 'NODE_CLI_FAILED: check runtime and file access; do not resubmit a task' }) + '\n');
    process.exitCode = 1;
  });
}
