import { ApiError, MOCK, clearTokens, getTokens, http, setTokens } from '../lib/http.js';
import { ROLES } from '../lib/perms.js';
import { loginRequest, logoutRequest, mockAccountFromTokens } from './auth.js';

const roleAliases = {
  admin: 'admin',
  circle_admin: 'admin',
  sacco_admin: 'admin',
  secretary: 'secretary',
  finance: 'finance',
  finance_officer: 'finance',
  loans: 'loans',
  loans_officer: 'loans',
  member: 'member',
  platform: 'platform',
  platform_owner: 'platform',
};

function roleKeysForMembership(membership) {
  const names = Array.isArray(membership.roles)
    ? membership.roles
    : [membership.role];
  return names.map(name => roleAliases[name]).filter(Boolean);
}

function toSessionUser(user) {
  const name = user.name || user.full_name || user.email || 'Member';
  const initials = user.initials
    || name.split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join('').toUpperCase();
  return {
    id: user.id,
    email: user.email,
    name,
    initials,
  };
}

function listFromResponse(response, key) {
  const list = Array.isArray(response) ? response : response && response[key];
  if (!Array.isArray(list)) throw new Error(`The ${key} response was not a list.`);
  return list;
}

function permissionsForRoles(roleKeys) {
  return [...new Set(roleKeys.flatMap(role => ROLES[role].perms))];
}

async function loadPermissions(saccoId, roleKeys) {
  try {
    const response = await http.get('/members/me/permissions', {
      params: saccoId == null ? undefined : { sacco_id: saccoId },
    });
    if (!response || !Array.isArray(response.permissions)) {
      throw new Error('The permissions response did not contain a permissions list.');
    }
    return response.permissions;
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 405)) {
      return permissionsForRoles(roleKeys);
    }
    throw error;
  }
}

async function buildSession(user, saccos) {
  const memberships = Array.isArray(user.memberships) ? user.memberships : [];
  const membership = memberships.find(item => item.status === 'active') || memberships[0] || null;
  const roleKeys = membership ? roleKeysForMembership(membership) : [];
  const isPlatform = Boolean(user.is_platform_owner) || roleKeys.includes('platform');

  if (membership && roleKeys.length === 0 && !isPlatform) {
    throw new Error('The signed-in membership has an unsupported role.');
  }

  const role = isPlatform ? 'platform' : roleKeys[0] || 'member';
  const saccoId = isPlatform || !membership ? null : membership.sacco_id;
  const sacco = saccoId == null ? null : saccos.find(item => String(item.id) === String(saccoId)) || null;
  const fallbackRoles = isPlatform ? ['platform'] : roleKeys;
  const perms = MOCK
    ? permissionsForRoles(fallbackRoles)
    : await loadPermissions(saccoId, fallbackRoles);

  return {
    user: toSessionUser(user),
    role,
    perms,
    can: permission => perms.includes(permission),
    saccoId,
    sacco,
  };
}

async function loadCurrentSession(user = null) {
  const currentUser = user || await http.get('/members/me');
  const saccosResponse = await http.get('/members/me/saccos');
  return buildSession(currentUser, listFromResponse(saccosResponse, 'saccos'));
}

export async function restoreSession() {
  const tokens = getTokens();
  if (!tokens) return null;

  if (MOCK) {
    const mockAccount = mockAccountFromTokens(tokens);
    if (!mockAccount) {
      clearTokens();
      return null;
    }
    return buildSession(mockAccount.user, mockAccount.saccos);
  }

  return loadCurrentSession();
}

export async function signIn(email, password, selectedRole) {
  const result = await loginRequest(email, password, selectedRole);
  setTokens({ access: result.access_token, refresh: result.refresh_token });

  try {
    if (MOCK) return buildSession(result.user, result.saccos);
    return await loadCurrentSession(result.user);
  } catch (error) {
    clearTokens();
    throw error;
  }
}

export async function signOut() {
  try {
    await logoutRequest();
  } finally {
    clearTokens();
  }
}
