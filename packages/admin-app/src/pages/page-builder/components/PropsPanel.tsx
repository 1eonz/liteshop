import type { ChangeEvent, JSX } from 'react';
import type { StoreComponentSchema, StorePageSchema } from '@liteshop/shared-types';
import { componentLabel } from '../model/page-builder-model';

interface PropsPanelProps {
  page: StorePageSchema;
  selected: StoreComponentSchema | null;
  isSite: boolean;
  onPropChange: (key: string, value: string) => void;
  onStyleChange: (key: string, value: string) => void;
  onAnimationChange: (type: string) => void;
  onSeoChange: (key: 'title' | 'description', value: string) => void;
}

/** 右侧组件属性、设计 Token、动画和 SEO 编辑面板。 */
export function PropsPanel({
  page,
  selected,
  isSite,
  onPropChange,
  onStyleChange,
  onAnimationChange,
  onSeoChange,
}: PropsPanelProps): JSX.Element {
  const contentKey =
    selected?.type === 'RichText'
      ? 'text'
      : selected?.type === 'SearchBar'
        ? 'placeholder'
        : 'title';
  const contentValue = selected
    ? String(selected.props.title ?? selected.props.text ?? selected.props.placeholder ?? '')
    : '';
  const handleSeo =
    (key: 'title' | 'description') =>
    (event: ChangeEvent<HTMLInputElement>): void =>
      onSeoChange(key, event.target.value);

  return (
    <aside className="panel builder-inspector" aria-label="属性面板">
      <div className="panel-title">
        <h2>属性</h2>
        <span>{selected ? componentLabel(selected.type) : '未选择'}</span>
      </div>
      {selected ? (
        <>
          <label className="builder-field">
            内容
            <input
              value={contentValue}
              onChange={(event) => onPropChange(contentKey, event.target.value)}
            />
          </label>
          <label className="builder-field">
            背景 Token
            <select
              value={selected.style.backgroundColor ?? ''}
              onChange={(event) => onStyleChange('backgroundColor', event.target.value)}
            >
              <option value="">默认背景</option>
              <option value="var(--color-primary-50)">主色浅</option>
              <option value="var(--color-warning-50)">警示浅</option>
              <option value="var(--color-surface)">表面色</option>
            </select>
          </label>
          <label className="builder-field">
            圆角 Token
            <select
              value={selected.style.borderRadius ?? ''}
              onChange={(event) => onStyleChange('borderRadius', event.target.value)}
            >
              <option value="">默认圆角</option>
              <option value="var(--radius-md)">中圆角</option>
              <option value="var(--radius-lg)">大圆角</option>
              <option value="var(--radius-full)">胶囊</option>
            </select>
          </label>
          <label className="builder-field">
            内边距 Token
            <select
              value={selected.style.padding ?? ''}
              onChange={(event) => onStyleChange('padding', event.target.value)}
            >
              <option value="">默认间距</option>
              <option value="var(--spacing-3)">紧凑</option>
              <option value="var(--spacing-4)">标准</option>
              <option value="var(--spacing-5)">宽松</option>
            </select>
          </label>
          {isSite && (
            <>
              <label className="builder-field">
                动画
                <select
                  value={selected.animation?.type ?? 'none'}
                  onChange={(event) => onAnimationChange(event.target.value)}
                >
                  <option value="none">关闭</option>
                  <option value="fade-up">向上淡入</option>
                  <option value="fade-down">向下淡入</option>
                  <option value="fade-left">向左淡入</option>
                  <option value="fade-right">向右淡入</option>
                  <option value="zoom-in">缩放进入</option>
                </select>
              </label>
              <label className="builder-field">
                SEO 标题
                <input
                  value={String(page.seo?.title ?? '')}
                  maxLength={120}
                  onChange={handleSeo('title')}
                />
              </label>
              <label className="builder-field">
                SEO 描述
                <input
                  value={String(page.seo?.description ?? '')}
                  maxLength={300}
                  onChange={handleSeo('description')}
                />
              </label>
            </>
          )}
        </>
      ) : (
        <p className="feedback">选择画布中的组件开始编辑。</p>
      )}
    </aside>
  );
}
