/*
 * The platform-owner flag is not on /members/me. It arrives in the sign-in reply, so a session
 * rebuilt from /members/me after a page reload used to lose it, and every /pf-* page answered 403.
 *
 * /members/me/permissions with no sacco_id answers 200 only for a platform owner, and 400 for
 * everyone else, so a 200 carrying a permissions list is the answer. The list itself is named by
 * what the permissions allow (sacco.manage, admin.manage, ...) and never contains the word
 * 'platform', which is what the old check looked for.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get } = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock('../lib/http.js', () => {
  class ApiError extends Error {
    constructor(status, code, message) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.code = code;
    }
  }
  return {
    ApiError,
    MOCK: false,
    mockDelay: () => Promise.resolve(),
    getTokens: () => ({ access: 'access-token', refresh: 'refresh-token' }),
    setTokens: () => {},
    clearTokens: () => {},
    onSessionEnded: () => {},
    http: { get, post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn() },
  };
});

import { ApiError } from '../lib/http.js';
import { restoreSession } from './session.js';

/* What the API answers for a platform owner with no sacco_id: OWNER_PLATFORM in
 * backend/app/security/permissions.py. No 'platform' in it, by design. */
const OWNER_PERMISSIONS = [
  'admin.manage',
  'dashboard.view',
  'sacco.manage',
  'sacco.update',
  'sacco.view',
];

const MEMBER = {
  id: 7,
  email: 'owner@example.com',
  name: 'Platform Owner',
  memberships: [],
};

function serveUser(user, permissionAnswer) {
  get.mockImplementation(async path => {
    if (path === '/members/me') return user;
    if (path === '/members/me/saccos') return { saccos: [] };
    if (path === '/members/me/permissions') return permissionAnswer();
    throw new Error(`unexpected request: ${path}`);
  });
}

const permissionCalls = () =>
  get.mock.calls.filter(([path]) => path === '/members/me/permissions').length;

beforeEach(() => {
  get.mockReset();
});

describe('a session rebuilt after a reload', () => {
  it('keeps platform-owner access when the permissions answer holds no "platform"', async () => {
    serveUser(MEMBER, () => ({ permissions: OWNER_PERMISSIONS }));

    const session = await restoreSession();

    expect(session.role).toBe('platform');
    expect(session.perms).toContain('platform');
    expect(session.sourceUser.is_platform_owner).toBe(true);
  });

  it('asks the permissions route twice: once to probe, once to load them', async () => {
    serveUser(MEMBER, () => ({ permissions: OWNER_PERMISSIONS }));

    await restoreSession();

    expect(permissionCalls()).toBe(2);
  });

  it('leaves an ordinary account alone when the probe answers 400', async () => {
    serveUser(MEMBER, () => {
      throw new ApiError(400, 'bad_request', 'sacco_id is required.');
    });

    const session = await restoreSession();

    expect(session.role).not.toBe('platform');
    expect(session.perms).not.toContain('platform');
    expect(session.sourceUser.is_platform_owner).toBeFalsy();
  });

  it('does not probe when the reply already carries the flag', async () => {
    serveUser({ ...MEMBER, is_platform_owner: true }, () => ({ permissions: OWNER_PERMISSIONS }));

    const session = await restoreSession();

    expect(session.role).toBe('platform');
    expect(permissionCalls()).toBe(1); // loading them for the session, not probing
  });

  it('does not probe an account that has an active membership', async () => {
    serveUser(
      { ...MEMBER, memberships: [{ membership_id: 3, sacco_id: 1, role: 'member', status: 'active' }] },
      () => ({ permissions: ['member.view'] }),
    );

    const session = await restoreSession();

    expect(session.role).toBe('member');
    // One call, for the landing SACCO's permissions. A second would be the owner probe.
    expect(permissionCalls()).toBe(1);
  });
});
