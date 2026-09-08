import type { JSX } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuditLogsQuery, useDebounceAction } from '../../hooks';
import { useRbacMutations, useRbacQuery } from '../../features/rbac';
import type { AdminRole } from '@liteshop/shared-types';

/** 审计与 RBAC 页面，帮助管理员核对菜单按钮权限和操作轨迹。 */
export function AuditPage(): JSX.Element {
  const logs = useAuditLogsQuery();
  const rbac = useRbacQuery();
  const mutations = useRbacMutations();
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [roleName, setRoleName] = useState('');
  const [rolePermissionCodes, setRolePermissionCodes] = useState<string[]>([]);
  const [userRoleDrafts, setUserRoleDrafts] = useState<Record<number, number[]>>({});
  const [feedback, setFeedback] = useState('');
  const permissionCodes = useMemo(
    () => (rbac.permissions.data ?? []).map((permission) => permission.code),
    [rbac.permissions.data],
  );
  const rbacQueryFailed = rbac.roles.isError || rbac.permissions.isError || rbac.users.isError;

  useEffect(() => {
    const drafts = Object.fromEntries(
      (rbac.users.data ?? []).map((user) => [user.id, user.roleIds]),
    );
    setUserRoleDrafts(drafts);
  }, [rbac.users.data]);

  const beginCreate = useCallback(() => {
    setEditingRoleId(null);
    setRoleName('');
    setRolePermissionCodes([]);
    setFeedback('');
  }, []);

  const beginEdit = useCallback((role: AdminRole) => {
    setEditingRoleId(role.id);
    setRoleName(role.name);
    setRolePermissionCodes(role.permissions);
    setFeedback('');
  }, []);

  const saveRole = useCallback(async () => {
    const name = roleName.trim();
    if (!name) {
      setFeedback('角色名称不能为空。');
      return;
    }
    setFeedback('');
    try {
      if (editingRoleId === null) {
        await mutations.create.mutateAsync({ name, permissionCodes: rolePermissionCodes });
      } else {
        await mutations.update.mutateAsync({
          roleId: editingRoleId,
          name,
          permissionCodes: rolePermissionCodes,
        });
      }
      beginCreate();
      setFeedback('角色已保存。');
    } catch {
      setFeedback('角色保存失败，请检查名称和权限后重试。');
    }
  }, [
    beginCreate,
    editingRoleId,
    mutations.create,
    mutations.update,
    roleName,
    rolePermissionCodes,
  ]);

  const removeRole = useCallback(
    async (role: AdminRole) => {
      if (!window.confirm(`确认删除角色“${role.name}”吗？`)) return;
      setFeedback('');
      try {
        await mutations.remove.mutateAsync(role.id);
        if (editingRoleId === role.id) beginCreate();
        setFeedback('角色已删除。');
      } catch {
        setFeedback('角色删除失败，仍绑定管理员的角色不能删除。');
      }
    },
    [beginCreate, editingRoleId, mutations.remove],
  );

  const saveUserRoles = useCallback(
    async (userId: number) => {
      setFeedback('');
      try {
        await mutations.updateUserRoles.mutateAsync({
          userId,
          roleIds: userRoleDrafts[userId] ?? [],
        });
        setFeedback('管理员角色已更新。');
      } catch {
        setFeedback('管理员角色更新失败，请检查权限后重试。');
      }
    },
    [mutations.updateUserRoles, userRoleDrafts],
  );

  const [runSaveRole, savingRole] = useDebounceAction(saveRole, 800);
  const [runRemoveRole, removingRole] = useDebounceAction(removeRole, 500);
  const [runSaveUserRoles, savingUserRoles] = useDebounceAction(saveUserRoles, 500);

  return (
    <div className="editor-page">
      <header>
        <div>
          <p>安全与权限</p>
          <h1>操作审计</h1>
        </div>
      </header>
      {rbacQueryFailed && (
        <p className="feedback error-state" role="alert">
          权限数据加载失败，请确认当前账号具有权限管理访问权后重试。
        </p>
      )}
      <section className="panel">
        <div className="panel-title">
          <h2>角色权限</h2>
          <span>{rbac.roles.data?.length ?? 0} 个角色</span>
        </div>
        {rbac.roles.data?.length ? (
          rbac.roles.data.map((role) => (
            <article className="audit-role" key={role.id}>
              <strong>{role.name}</strong>
              <span>{role.permissions.join('、') || '暂无权限'}</span>
            </article>
          ))
        ) : (
          <div className="feedback">暂无角色数据，数据库初始化后显示。</div>
        )}
        <p className="muted">系统权限点 {rbac.permissions.data?.length ?? 0} 个</p>
      </section>
      <section className="panel">
        <div className="panel-title">
          <h2>最近操作</h2>
          <span>最多 100 条</span>
        </div>
        {logs.isLoading ? (
          <div className="feedback">日志加载中…</div>
        ) : logs.data?.length ? (
          <div className="audit-list">
            {logs.data.map((log) => (
              <article className="audit-log" key={log.id}>
                <div>
                  <strong>{log.action}</strong>
                  <span>
                    {log.resourceType} #{log.resourceId ?? '-'}
                  </span>
                </div>
                <time dateTime={log.createdAt}>
                  {new Date(log.createdAt).toLocaleString('zh-CN')}
                </time>
                <small>{log.requestId}</small>
              </article>
            ))}
          </div>
        ) : (
          <div className="feedback">暂无操作日志。</div>
        )}
      </section>
      {feedback && (
        <p className="feedback" role="status">
          {feedback}
        </p>
      )}
      <section className="panel" aria-label="角色管理">
        <div className="panel-title">
          <h2>角色管理</h2>
          <button className="ghost-button" type="button" onClick={beginCreate}>
            新建角色
          </button>
        </div>
        <div className="role-management">
          <div className="role-list">
            {rbac.roles.data?.length ? (
              rbac.roles.data.map((role) => (
                <article className="audit-role" key={role.id}>
                  <div>
                    <strong>{role.name}</strong>
                    <span>{role.permissions.join('、') || '暂无权限'}</span>
                  </div>
                  <div className="row-actions">
                    <button className="ghost-button" type="button" onClick={() => beginEdit(role)}>
                      编辑
                    </button>
                    <button
                      className="danger-button"
                      type="button"
                      disabled={removingRole}
                      onClick={() => void runRemoveRole(role)}
                    >
                      删除
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <div className="feedback">暂无角色数据。</div>
            )}
          </div>
          <form
            className="editor-form role-editor"
            onSubmit={(event) => {
              event.preventDefault();
              void runSaveRole();
            }}
          >
            <h3>{editingRoleId === null ? '新建角色' : '编辑角色'}</h3>
            <label>
              角色名称
              <input
                value={roleName}
                maxLength={64}
                onChange={(event) => setRoleName(event.target.value)}
              />
            </label>
            <fieldset className="permission-checks">
              <legend>权限点</legend>
              {permissionCodes.length ? (
                permissionCodes.map((code) => (
                  <label className="checkbox-field" key={code}>
                    <input
                      type="checkbox"
                      checked={rolePermissionCodes.includes(code)}
                      onChange={(event) =>
                        setRolePermissionCodes((current) =>
                          event.target.checked
                            ? [...current, code]
                            : current.filter((item) => item !== code),
                        )
                      }
                    />
                    {code}
                  </label>
                ))
              ) : (
                <p className="muted">暂无可分配权限点。</p>
              )}
            </fieldset>
            <div className="row-actions">
              <button type="submit" disabled={savingRole}>
                {savingRole ? '保存中…' : '保存角色'}
              </button>
              {editingRoleId !== null && (
                <button className="ghost-button" type="button" onClick={beginCreate}>
                  取消编辑
                </button>
              )}
            </div>
          </form>
        </div>
      </section>
      <section className="panel" aria-label="管理员角色分配">
        <div className="panel-title">
          <h2>管理员分配</h2>
          <span>{rbac.users.data?.length ?? 0} 个账号</span>
        </div>
        {rbac.users.data?.length ? (
          <div className="admin-user-list">
            {rbac.users.data.map((user) => {
              const selectedRoleIds = userRoleDrafts[user.id] ?? user.roleIds;
              return (
                <article className="admin-user-row" key={user.id}>
                  <div>
                    <strong>{user.nickname || '未设置昵称'}</strong>
                    <span>{user.phone}</span>
                  </div>
                  <div className="permission-checks">
                    {(rbac.roles.data ?? []).map((role) => (
                      <label className="checkbox-field" key={role.id}>
                        <input
                          type="checkbox"
                          checked={selectedRoleIds.includes(role.id)}
                          onChange={(event) =>
                            setUserRoleDrafts((current) => ({
                              ...current,
                              [user.id]: event.target.checked
                                ? [...selectedRoleIds, role.id]
                                : selectedRoleIds.filter((id) => id !== role.id),
                            }))
                          }
                        />
                        {role.name}
                      </label>
                    ))}
                  </div>
                  <button
                    type="button"
                    disabled={savingUserRoles}
                    onClick={() => void runSaveUserRoles(user.id)}
                  >
                    {savingUserRoles ? '保存中…' : '保存分配'}
                  </button>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="feedback">暂无可分配的管理员账号。</div>
        )}
      </section>
    </div>
  );
}
