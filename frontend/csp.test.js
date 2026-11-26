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

const headerNamed = headers =>
  headers.find(header => header.key.toLowerCase() === 'content-security-policy');

const policyHeaders = vercel.headers.map(rule => headerNamed(rule.headers)).filter(Boolean);
const policy = policyHeaders[0] ? policyHeaders[0].value : '';

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

describe('the policy in vercel.json', () => {
  it('is sent, on every path, with a script-src', () => {
    expect(policyHeaders).toHaveLength(1);
    expect(policy).toContain("default-src 'self'");
    expect(directive('script-src')).not.toBe('');
  });

  it('finds exactly one inline script to pin: the theme boot', () => {
    expect(inlineScripts).toHaveLength(1);
    expect(inlineScripts[0]).toContain('nexora.appearance');
  });

  it('pins that script by the hash index.html currently produces', () => {
    const digest = createHash('sha256').update(inlineScripts[0]).digest('base64');
    expect(hashes(directive('script-src'))).toContain(`sha256-${digest}`);
  });

  it('does not carry a second, stale hash in script-src', () => {
    expect(hashes(directive('script-src'))).toHaveLength(1);
  });
});
