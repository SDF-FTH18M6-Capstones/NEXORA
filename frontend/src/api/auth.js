import { ApiError, MOCK, getTokens, http, mockDelay } from '../lib/http.js';
import { ROLES } from '../lib/perms.js';
import { me, mySaccos } from '../mocks/data.js';

const mockRoleNames = {
  admin: 'sacco_admin',
  secretary: 'secretary',
  finance: 'finance_officer',
  loans: 'loans_officer',
  member: 'member',
  platform: 'platform_owner',
};

function makeMockAccount(role, email) {
  const permissions = ROLES[role].perms;
  const platformOwner = permissions.includes('platform');
  const memberships = platformOwner
    ? []
    : [{ membership_id: 1, sacco_id: 1, role: mockRoleNames[role], status: 'active' }];
  return {
    user: {
      id: `mock-${role}`,
      email: email || me.email,
      name: me.name,
      initials: me.initials,
      is_platform_owner: platformOwner,
      memberships,
    },
    saccos: platformOwner ? [] : mySaccos,
    access_token: `mock:${role}`,
    refresh_token: `mock:${role}`,
  };
}

export async function loginRequest(email, password, selectedRole = 'member') {
  if (MOCK) {
    await mockDelay(250);
    if (password !== 'demo') {
      throw new ApiError(401, 'unauthorized', 'Your email or password is not right.');
    }
    const role = Object.hasOwn(ROLES, selectedRole) ? selectedRole : 'member';
    return makeMockAccount(role, email);
  }

  return http.post('/auth/login', {
    body: { email, password },
    auth: false,
  });
}

export function mockAccountFromTokens(tokens = getTokens()) {
  if (!MOCK || !tokens || !tokens.access || !tokens.access.startsWith('mock:')) return null;
  const role = tokens.access.slice('mock:'.length);
  return Object.hasOwn(ROLES, role) ? makeMockAccount(role) : null;
}

export async function logoutRequest() {
  if (MOCK) return;
  const tokens = getTokens();
  if (!tokens) return;

  try {
    await http.post('/auth/logout', {
      body: { refresh_token: tokens.refresh },
      token: tokens.access,
      auth: false,
    });
  } catch {
    // Logout must clear local tokens even when the API cannot be reached.
  }
}
