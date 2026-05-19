# Password Change — Design Spec

**Date:** 2026-05-19
**Status:** Approved (pre-implementation)

## Goal

Allow an authenticated user to change their own password, reusing the same
validation rule as signup (minimum 8 characters), with current-password
verification and full session invalidation after a successful change.

## Out of Scope

- Forgot-password / email-reset flow.
- Admin-driven password reset for another user.
- Password complexity rules beyond the existing 8-character minimum.
- Password history / "cannot reuse last N passwords".

## Security Decisions

1. **Current password required.** Prevents a stolen access token from being
   used to lock out the legitimate owner. The endpoint requires both a valid
   Bearer access token AND the current password.
2. **Full session invalidation after change.** On success the user's
   `refresh_jti` is cleared; every active refresh token across all devices is
   invalidated. The route also clears the HttpOnly refresh cookie on the
   current response. The frontend wipes local auth state and redirects to
   `/login`.
3. **Same generic error for current-password mismatch and new==current.** Each
   condition gets a distinct human message but the same HTTP 400 status.
   No information leak — both are user errors, not credential oracles.
4. **Rate limit 5/min** (keyed by IP via slowapi), matching `/auth/login`.
   Deters online brute-force of `current_password`.

## Backend

### Schema (`backend/src/schemas/auth.py`)

```python
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError("password must be at least 8 characters")
        return v
```

Reuses the existing `_MIN_PASSWORD_LEN = 8` constant — same rule as `UserCreate`.

### Service (`backend/src/services/auth_service.py`)

```python
async def change_password(
    self, user_id: uuid.UUID, data: PasswordChangeRequest
) -> None:
    """Verify current password, hash + persist new one, invalidate all sessions.

    Raises 400 if the current password is wrong, or if the new password
    matches the current one. Caller (the route) is responsible for clearing
    the refresh cookie on the response.
    """
```

Behavior:

1. `SELECT User WHERE id = user_id`. Defensive 401 if missing or inactive
   (the dependency `get_current_user` already filters these out, but the
   service revalidates so it is safe to call from other entry points later).
2. `_verify_password(current_password, user.password_hash)` — false → 400
   `"Current password is incorrect"`.
3. `new_password == current_password` (plain string equality — both are
   already in memory; running a second bcrypt round here is needless
   latency) → 400 `"New password must be different from current password"`.
4. `user.password_hash = _hash_password(new_password)`.
5. `user.refresh_jti = None`.
6. `await self.session.commit()`.

### Route (`backend/src/api/routes/auth.py`)

```python
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    response: Response,
    data: PasswordChangeRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await auth_service.change_password(current_user.id, data)
    _clear_refresh_cookie(response)
```

Responses:

- **204** — success; refresh cookie cleared in the same response.
- **401** — Bearer header missing/invalid/expired, or user inactive.
- **400** — `Current password is incorrect` OR `New password must be different from current password`.
- **422** — `new_password` shorter than 8 characters (Pydantic validation).
- **429** — rate limit exceeded.

### Tests

`tests/test_auth_service.py` — new `TestChangePassword` class:

- `test_success_updates_hash_and_clears_refresh_jti` — happy path; assert
  `password_hash` is rehashed (different value AND verifies against new) and
  `refresh_jti is None` and `commit` was awaited.
- `test_wrong_current_password_raises_400` — does NOT touch
  `password_hash`/`refresh_jti`.
- `test_new_equals_current_raises_400`.
- Follow the existing `AsyncMock(spec=AsyncSession)` + `_make_execute_result`
  pattern in this file.

`tests/test_routes_auth.py` — new `TestChangePassword` class:

- `test_success_returns_204_and_clears_cookie` — assert `Set-Cookie` clears
  `refresh_token` with `Path=/api/v1/auth`.
- `test_missing_bearer_returns_401`.
- `test_wrong_current_password_returns_400`.
- `test_new_equals_current_returns_400`.
- `test_short_new_password_returns_422`.
- Use the `auth_client` fixture; override `get_current_user` to inject a
  fake user (same pattern as `TestMe`).

## Frontend

### API client (`frontend/lib/api/auth.ts`)

```typescript
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await apiClient("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  if (!res.ok) {
    let detail = "Failed to change password"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  useAuthStore.getState().clearAuth()
}
```

Notes:

- Uses `apiClient` so the Bearer header and `credentials: "include"` are
  attached automatically (matches the `apiRegister`/`login` pattern in the
  same file).
- On 204, immediately clears local auth state so the in-memory access token
  cannot be used after the password was rotated.

### UI component (`frontend/components/profile/ChangePasswordCard.tsx`)

New client component mounted below the existing account-details card in
`frontend/app/(app)/(chat)/profile/page.tsx`.

Three fields: `currentPassword`, `newPassword`, `confirmPassword` (all
`type="password"`). Submit button labeled `change password` (lowercase to
match the existing profile page styling).

Zod schema:

```typescript
const schema = z.object({
  currentPassword: z.string().min(1, "Current password is required"),
  newPassword: z.string().min(8, "Minimum 8 characters"),
  confirmPassword: z.string(),
})
.refine(d => d.newPassword === d.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})
.refine(d => d.newPassword !== d.currentPassword, {
  message: "New password must be different from current",
  path: ["newPassword"],
})
```

On submit:

```typescript
try {
  await changePassword(data.currentPassword, data.newPassword)
  toast.success("Password changed. Please sign in again.")
  router.push("/login")
} catch (err) {
  toast.error(err instanceof Error ? err.message : "Failed to change password")
}
```

`changePassword` already calls `clearAuth()` on success, so the
`/login` navigation lands on a clean unauthenticated state.

### Profile page edit

`frontend/app/(app)/(chat)/profile/page.tsx` — add `<ChangePasswordCard />`
immediately after the existing `<Card>` (still inside the `max-w-2xl`
wrapper, with a `mt-6` or equivalent gap).

## Files Changed

- `backend/src/schemas/auth.py` (add `PasswordChangeRequest`)
- `backend/src/services/auth_service.py` (add `change_password`)
- `backend/src/api/routes/auth.py` (add route)
- `backend/tests/test_auth_service.py` (new test class)
- `backend/tests/test_routes_auth.py` (new test class)
- `frontend/lib/api/auth.ts` (add `changePassword`)
- `frontend/components/profile/ChangePasswordCard.tsx` (new file)
- `frontend/app/(app)/(chat)/profile/page.tsx` (mount the card)

## Alternatives Considered

- **Endpoint at `/users/me/password`.** Rejected: credential and
  token-related operations live under `/api/v1/auth/*` in this project
  (`login`, `refresh`, `logout`, `register`); keeping `change-password`
  there preserves coherence and lets it share `_clear_refresh_cookie` and
  the slowapi rate-limit pattern.
- **Extend `UserUpdate` with an optional `password` field.** Rejected:
  `UserUpdate` is a generic PATCH used by both the user themselves and
  admins; mixing it with a flow that requires `current_password`
  verification would either break admin updates or open a route where an
  admin could rotate any user's password without their consent.
- **Do not require current password.** Rejected per user decision —
  keeps standard security practice.
- **Keep current session alive, only invalidate others.** Rejected per
  user decision — a password change should force re-authentication
  everywhere.
