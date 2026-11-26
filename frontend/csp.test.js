/*
 * vercel.json pins the one inline script in index.html by its SHA-256, because the CSP allows
 * no other inline script. Edit that script — a new dataset key, a typo fix — and the hash stops
 * matching: the build still succeeds, nothing fails, and production silently drops the script,
 * so every visitor gets the default look instead of their saved theme.
 *
 * This file is the alarm. It fails on the commit that would break it, not on the deploy.
 *
 * The hash covers the script with CRLF folded to LF, because the HTML parser normalises
 * newlines before a script is hashed; a Windows checkout and a Linux build must agree.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const here = new URL('.', import.meta.url);
const html = readFileSync(new URL('index.html', here), 'utf8');
const vercel = JSON.parse(readFileSync(new URL('vercel.json', here), 'utf8'));

/* No policy at all is a missing CSP, so it has to be reported as one: reading `vercel.headers`
 * straight through would throw a TypeError while this file loads, which says nothing useful. */
const rules = Array.isArray(vercel.headers) ? vercel.headers : [];
const policyHeaders = rules
  .flatMap(rule => (Array.isArray(rule.headers) ? rule.headers : []))
  .filter(header => String(header.key || '').toLowerCase() === 'content-security-policy');
const policy = policyHeaders.length ? String(policyHeaders[0].value || '') : '';

const directive = name =>
  policy
    .split(';')
    .map(part => part.trim())
    .find(part => part === name || part.startsWith(`${name} `)) || '';

const hashes = text => [...text.matchAll(/'sha256-[A-Za-z0-9+/=]+'/g)].map(m => m[0].slice(1, -1));

/* Every inline script: a <script> tag with no src attribute. The body's module script has one,
 * so only the boot script in <head> should survive this filter. */
const inlineScripts = [...html.matchAll(/<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(
  match => match[1].replace(/\r\n/g, '\n'),
);

const NO_POLICY = 'vercel.json declares no Content-Security-Policy header';

describe('the policy in vercel.json', () => {
  it('is sent, on every path, with a script-src', () => {
    expect(policyHeaders, NO_POLICY).toHaveLength(1);
    expect(policy, "the policy has no default-src 'self'").toContain("default-src 'self'");
    expect(directive('script-src'), 'the policy has no script-src directive').not.toBe('');
  });

  it('finds exactly one inline script to pin: the theme boot', () => {
    expect(inlineScripts).toHaveLength(1);
    expect(inlineScripts[0]).toContain('nexora.appearance');
  });

  it('pins that script by the hash index.html currently produces', () => {
    const scriptSrc = directive('script-src');
    expect(scriptSrc, 'the policy has no script-src directive to pin a hash in').not.toBe('');
    const digest = createHash('sha256').update(inlineScripts[0]).digest('base64');
    expect(hashes(scriptSrc), `script-src should pin sha256-${digest}`).toContain(
      `sha256-${digest}`,
    );
  });

  it('does not carry a second, stale hash in script-src', () => {
    expect(hashes(directive('script-src')), NO_POLICY).toHaveLength(1);
  });
});
