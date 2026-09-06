import type { JSX } from 'react';
import { useAuditLogsQuery, useRbacQuery } from '../../hooks';

/** 审计与 RBAC 页面，帮助管理员核对菜单按钮权限和操作轨迹。 */
export function AuditPage(): JSX.Element {
  const logs = useAuditLogsQuery();
  const rbac = useRbacQuery();
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>安全与权限</p>
          <h1>操作审计</h1>
        </div>
      </header>
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
    </div>
  );
}
