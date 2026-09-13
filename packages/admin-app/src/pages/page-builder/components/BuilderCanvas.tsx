import type { DragEvent, JSX, KeyboardEvent } from 'react';
import type { StoreComponentSchema, StorePageSchema } from '@liteshop/shared-types';
import { componentLabel, openPagePreview, previewCopy } from '../model/page-builder-model';

interface ManagedPage {
  id: number;
  slug: string;
  name: string;
  isHome: boolean;
  channel?: 'store' | 'site';
}

interface BuilderCanvasProps {
  page: StorePageSchema;
  pages: ManagedPage[];
  selectedId: string | null;
  zoom: number;
  isSite: boolean;
  copyingPage: boolean;
  settingHome: boolean;
  componentTypes: StoreComponentSchema['type'][];
  onPageChange: (pageId: number) => void;
  onSelect: (id: string) => void;
  onDropComponent: (type: StoreComponentSchema['type']) => void;
  onMove: (direction: -1 | 1) => void;
  onDuplicate: () => void;
  onRemove: () => void;
  onPreviewNotice: (message: string) => void;
  onCopyPage: () => void;
  onSetHome: () => void;
}

/** 中间画布及其页面工具栏，负责拖放和组件排序交互。 */
export function BuilderCanvas({
  page,
  pages,
  selectedId,
  zoom,
  isSite,
  copyingPage,
  settingHome,
  componentTypes,
  onPageChange,
  onSelect,
  onDropComponent,
  onMove,
  onDuplicate,
  onRemove,
  onPreviewNotice,
  onCopyPage,
  onSetHome,
}: BuilderCanvasProps): JSX.Element {
  const handleDrop = (event: DragEvent<HTMLElement>): void => {
    event.preventDefault();
    const type = event.dataTransfer.getData(
      'application/x-liteshop-component',
    ) as StoreComponentSchema['type'];
    if (componentTypes.includes(type)) onDropComponent(type);
  };

  const handleItemKeyDown = (event: KeyboardEvent<HTMLElement>, id: string): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect(id);
    }
  };

  return (
    <main className="builder-canvas-wrap" aria-label="页面画布">
      <div className="builder-canvas-wrap__bar">
        <label>
          页面
          <select value={page.id} onChange={(event) => onPageChange(Number(event.target.value))}>
            {pages
              .filter((item) => item.channel === page.channel || !item.channel)
              .map((item) => (
                <option value={item.id} key={item.id}>
                  {item.name} · /{item.slug}
                </option>
              ))}
          </select>
        </label>
        <button
          className="ghost-button"
          type="button"
          onClick={() =>
            onPreviewNotice(
              openPagePreview(page)
                ? '已打开 H5 草稿预览'
                : '浏览器阻止了预览窗口，请允许弹窗后重试',
            )
          }
        >
          预览
        </button>
        <button className="ghost-button" type="button" disabled={copyingPage} onClick={onCopyPage}>
          {copyingPage ? '复制中…' : '复制页面'}
        </button>
        <button className="ghost-button" type="button" disabled={settingHome} onClick={onSetHome}>
          {settingHome ? '设置中…' : '设为首页'}
        </button>
      </div>
      <div
        className={isSite ? 'builder-canvas builder-canvas--site' : 'builder-canvas'}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        style={{ transform: `scale(${zoom})` }}
      >
        {page.components.length ? (
          page.components.map((component, index) => (
            <article
              className={
                component.id === selectedId ? 'builder-item builder-item--selected' : 'builder-item'
              }
              key={component.id}
              tabIndex={0}
              onClick={() => onSelect(component.id)}
              onKeyDown={(event) => handleItemKeyDown(event, component.id)}
              style={component.style}
            >
              <div className="builder-item__head">
                <strong>{componentLabel(component.type)}</strong>
                <span>{component.type}</span>
              </div>
              <p>{previewCopy(component)}</p>
              {component.id === selectedId && (
                <div className="builder-item__actions">
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onMove(-1);
                    }}
                    disabled={index === 0}
                  >
                    上移
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onMove(1);
                    }}
                    disabled={index === page.components.length - 1}
                  >
                    下移
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onDuplicate();
                    }}
                  >
                    复制
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onRemove();
                    }}
                  >
                    删除
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <div className="builder-empty">
            <strong>画布为空</strong>
            <span>从左侧组件库添加模块，或拖拽到这里。</span>
          </div>
        )}
      </div>
    </main>
  );
}
