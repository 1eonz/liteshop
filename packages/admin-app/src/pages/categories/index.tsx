import type { FormEvent, JSX } from 'react';
import { useState } from 'react';
import { useAdminCategoriesQuery, useAdminCategoryMutations, useDebounceAction } from '../../hooks';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

/** 商品分类管理页面，支持新增、重命名和停用。 */
export function CategoriesPage(): JSX.Element {
  const query = useAdminCategoriesQuery();
  const mutations = useAdminCategoryMutations();
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const create = async (): Promise<void> => {
    if (!name.trim()) {
      setError('请输入分类名称。');
      return;
    }
    setError('');
    try {
      await mutations.create.mutateAsync({ name: name.trim() });
      setName('');
    } catch {
      setError('分类创建失败，请检查权限。');
    }
  };
  const [runCreate, creating] = useDebounceAction(create, 500);
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void runCreate();
  };
  const rename = async (categoryId: number, currentName: string): Promise<void> => {
    const next = window.prompt('输入新的分类名称', currentName)?.trim();
    if (!next || next === currentName) return;
    try {
      await mutations.update.mutateAsync({ categoryId, input: { name: next } });
    } catch {
      setError('分类更新失败，请稍后重试。');
    }
  };
  const [runRename, renaming] = useDebounceAction(rename, 500);
  const remove = async (categoryId: number): Promise<void> => {
    try {
      await mutations.remove.mutateAsync(categoryId);
    } catch {
      setError('分类停用失败，请稍后重试。');
    }
  };
  const [runRemove, removing] = useDebounceAction(remove, 500);
  if (query.isLoading)
    return (
      <div className="editor-page">
        <FeedbackState>分类加载中…</FeedbackState>
      </div>
    );
  if (query.isError)
    return (
      <div className="editor-page">
        <ErrorState onRetry={() => void query.refetch()}>分类加载失败，请刷新重试。</ErrorState>
      </div>
    );
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>商品中心</p>
          <h1>分类管理</h1>
        </div>
      </header>
      <form className="inline-create" onSubmit={submit}>
        <label>
          新增分类
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="例如：家居"
          />
        </label>
        <button className="primary-action" type="submit" disabled={creating}>
          {creating ? '创建中…' : '新增分类'}
        </button>
      </form>
      {error && (
        <p className="feedback error-state" role="alert">
          {error}
        </p>
      )}
      <section className="editor-form category-list" aria-label="分类列表">
        {(query.data ?? []).length ? (
          query.data?.map((category) => (
            <article className="category-row" key={category.id}>
              <div>
                <strong>{category.name}</strong>
                <span className="muted">排序 {category.sortOrder}</span>
              </div>
              <div className="row-actions">
                <button
                  type="button"
                  disabled={renaming || mutations.update.isPending}
                  onClick={() => void runRename(category.id, category.name)}
                >
                  重命名
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  disabled={removing || mutations.remove.isPending}
                  onClick={() => void runRemove(category.id)}
                >
                  停用
                </button>
              </div>
            </article>
          ))
        ) : (
          <div className="feedback">暂无分类，请先创建。</div>
        )}
      </section>
    </div>
  );
}
