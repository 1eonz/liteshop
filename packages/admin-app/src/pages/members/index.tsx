import type { JSX } from 'react';
import { useState } from 'react';
import { useDebounceAction } from '../../hooks';
import { useMemberMutations, useMemberQuery, useMembersQuery } from '../../hooks/useAdminQueries';
import { formatPrice } from '../../utils/format-price';

/** 会员管理页面，列表与详情在同一工作区内完成审阅和维护。 */
export function MembersPage(): JSX.Element {
  const membersQuery = useMembersQuery();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const detailQuery = useMemberQuery(selectedId);
  const mutations = useMemberMutations();
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState('');
  const saveTags = async () => {
    if (!selectedId) return;
    setError('');
    try {
      await mutations.updateTags.mutateAsync({
        userId: selectedId,
        tags: tagInput
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '标签保存失败，请重试。');
    }
  };
  const [save, saving] = useDebounceAction(saveTags, 500);
  const updateLevel = async (memberLevel: 'NORMAL' | 'MEMBER'): Promise<void> => {
    if (selectedId === null) return;
    setError('');
    try {
      await mutations.updateLevel.mutateAsync({ userId: selectedId, memberLevel });
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : '等级更新失败，请重试。');
    }
  };
  const [runUpdateLevel, updatingLevel] = useDebounceAction(updateLevel, 500);
  if (membersQuery.isLoading) {
    return (
      <div className="editor-page">
        <div className="feedback">会员加载中…</div>
      </div>
    );
  }
  if (membersQuery.isError) {
    return (
      <div className="editor-page">
        <div className="feedback error-state" role="alert">
          会员加载失败，请检查权限后重试。
        </div>
      </div>
    );
  }
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>用户运营</p>
          <h1>会员管理</h1>
        </div>
        <span className="list-status">共 {membersQuery.data?.meta.total ?? 0} 位会员</span>
      </header>
      <section className="editor-form product-list" aria-label="会员列表">
        {membersQuery.data?.items.map((member) => (
          <button
            className="admin-product-row"
            type="button"
            key={member.id}
            onClick={() => {
              setSelectedId(member.id);
              setTagInput(member.tags.join(', '));
            }}
          >
            <span>
              <strong>{member.nickname || '未设置昵称'}</strong>
              <small>{member.phone}</small>
            </span>
            <span>{member.memberLevel === 'MEMBER' ? '会员' : '普通用户'}</span>
            <span>{member.orderCount} 单</span>
            <span>{formatPrice(member.totalSpent)}</span>
          </button>
        ))}
      </section>
      {selectedId !== null && (
        <section className="panel" aria-label="会员详情">
          <div className="panel-title">
            <h2>会员详情</h2>
            <button className="ghost-button" type="button" onClick={() => setSelectedId(null)}>
              关闭
            </button>
          </div>
          {detailQuery.isLoading ? (
            <div className="feedback">详情加载中…</div>
          ) : detailQuery.isError ? (
            <div className="feedback error-state" role="alert">
              详情加载失败，请重试。
            </div>
          ) : (
            detailQuery.data && (
              <>
                <p>
                  {detailQuery.data.phone} · {detailQuery.data.points} 积分
                </p>
                <label>
                  标签（逗号分隔）
                  <input value={tagInput} onChange={(event) => setTagInput(event.target.value)} />
                </label>
                <button type="button" disabled={saving} onClick={() => void save()}>
                  {saving ? '保存中…' : '保存标签'}
                </button>
                <label>
                  等级
                  <select
                    value={detailQuery.data.memberLevel}
                    disabled={updatingLevel || mutations.updateLevel.isPending}
                    onChange={(event) =>
                      void runUpdateLevel(event.target.value as 'NORMAL' | 'MEMBER')
                    }
                  >
                    <option value="NORMAL">普通用户</option>
                    <option value="MEMBER">会员</option>
                  </select>
                </label>
                {error && (
                  <p className="feedback error-state" role="alert">
                    {error}
                  </p>
                )}
              </>
            )
          )}
        </section>
      )}
    </div>
  );
}
