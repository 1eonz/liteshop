import type { JSX, KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  StoreComponentSchema,
  StoreComponentType,
  StorePageSchema,
} from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import {
  copyManagedPage,
  listManagedPages,
  publishManagedPage,
  saveManagedPage,
  setManagedHome,
} from '../../service/pages';

const STORAGE_KEY = 'liteshop.page-builder.draft';
const MAX_HISTORY = 50;

const COMPONENT_GROUPS: Array<{ label: string; types: StoreComponentType[] }> = [
  { label: '基础内容', types: ['SearchBar', 'Carousel', 'ImageBanner', 'Spacer', 'RichText'] },
  {
    label: '商品运营',
    types: ['CategoryGrid', 'ProductGrid', 'ProductList', 'ProductCarousel', 'CouponBlock'],
  },
  { label: '转化组件', types: ['ActivityBanner', 'AnnouncementBar', 'Tabbar'] },
];

const DEFAULT_PAGE: StorePageSchema = {
  id: 1,
  slug: 'home',
  name: '首页',
  title: '商城首页',
  version: 1,
  isHome: true,
  components: [
    { id: 'search-1', type: 'SearchBar', props: { placeholder: '搜索商品' }, style: {} },
    { id: 'carousel-1', type: 'Carousel', props: { title: '精选活动' }, style: {} },
    { id: 'category-1', type: 'CategoryGrid', props: { columns: 4 }, style: {} },
    { id: 'product-1', type: 'ProductGrid', props: { columns: 2 }, style: {} },
    { id: 'banner-1', type: 'ActivityBanner', props: { title: '限时活动' }, style: {} },
    {
      id: 'tabbar-1',
      type: 'Tabbar',
      props: { items: ['home', 'category', 'cart', 'me'] },
      style: {},
    },
  ],
};

const TEMPLATES: Array<{ key: string; label: string; components: StoreComponentSchema[] }> = [
  { key: 'minimal', label: '简洁上新', components: DEFAULT_PAGE.components.slice(0, 4) },
  {
    key: 'campaign',
    label: '活动转化',
    components: [
      {
        id: 'announcement-template',
        type: 'AnnouncementBar',
        props: { text: '今日下单享包邮' },
        style: {},
      },
      {
        id: 'coupon-template',
        type: 'CouponBlock',
        props: { title: '新人券', description: '满 99 减 10' },
        style: {},
      },
      {
        id: 'product-carousel-template',
        type: 'ProductCarousel',
        props: { title: '热销推荐' },
        style: {},
      },
    ],
  },
  {
    key: 'content',
    label: '内容导购',
    components: [
      { id: 'image-template', type: 'ImageBanner', props: { title: '品牌故事' }, style: {} },
      {
        id: 'rich-text-template',
        type: 'RichText',
        props: { text: '用一段文字介绍你的品牌与服务。' },
        style: {},
      },
      { id: 'category-template', type: 'CategoryGrid', props: { columns: 4 }, style: {} },
    ],
  },
];

function readDraft(): StorePageSchema {
  if (typeof window === 'undefined') return DEFAULT_PAGE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PAGE;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return DEFAULT_PAGE;
    const draft = parsed as Partial<StorePageSchema>;
    if (!Array.isArray(draft.components)) return DEFAULT_PAGE;
    return { ...DEFAULT_PAGE, ...draft, components: draft.components as StoreComponentSchema[] };
  } catch {
    return DEFAULT_PAGE;
  }
}

function componentLabel(type: StoreComponentType): string {
  const labels: Record<StoreComponentType, string> = {
    SearchBar: '搜索框',
    Carousel: '轮播图',
    CategoryGrid: '分类导航',
    ProductGrid: '商品网格',
    ActivityBanner: '图片广告',
    Tabbar: '底部导航',
    RichText: '富文本',
    ImageBanner: '图片横幅',
    Spacer: '辅助空白',
    ProductList: '商品列表',
    ProductCarousel: '商品横滑',
    CouponBlock: '优惠券',
    AnnouncementBar: '公告栏',
  };
  return labels[type];
}

function previewCopy(component: StoreComponentSchema): string {
  const props = component.props;
  if (typeof props.title === 'string') return props.title;
  if (typeof props.text === 'string') return props.text;
  if (typeof props.placeholder === 'string') return props.placeholder;
  return componentLabel(component.type);
}

function openPreview(page: StorePageSchema): boolean {
  const previewBase = import.meta.env.VITE_H5_PREVIEW_URL ?? 'http://127.0.0.1:5173';
  const previewUrl = new URL('/preview', previewBase);
  previewUrl.searchParams.set('schema', JSON.stringify(page));
  const previewWindow = window.open(previewUrl.toString(), '_blank', 'noopener,noreferrer');
  return previewWindow !== null;
}

/** 商城低代码搭建器：三栏画布、50 步撤销重做、自动保存、模板和预览。 */
export function PageBuilderPage(): JSX.Element {
  const [page, setPage] = useState<StorePageSchema>(readDraft);
  const [history, setHistory] = useState<StorePageSchema[]>([]);
  const [future, setFuture] = useState<StorePageSchema[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pages, setPages] = useState<
    Array<{ id: number; slug: string; name: string; isHome: boolean }>
  >([]);
  const [zoom, setZoom] = useState(1);
  const [notice, setNotice] = useState('草稿已加载');
  const pageRef = useRef(page);
  pageRef.current = page;

  const selected = useMemo(
    () => page.components.find((component) => component.id === selectedId) ?? null,
    [page.components, selectedId],
  );

  useEffect(() => {
    let active = true;
    void listManagedPages()
      .then((items) => {
        if (active) setPages(items);
      })
      .catch(() => {
        if (active) setPages([{ id: 1, slug: 'home', name: '首页', isHome: true }]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(pageRef.current));
      setNotice('已自动保存草稿');
    }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const updatePage = useCallback((updater: (current: StorePageSchema) => StorePageSchema): void => {
    setPage((current) => {
      const next = updater(current);
      setHistory((items) => [...items, current].slice(-MAX_HISTORY));
      setFuture([]);
      return next;
    });
    setNotice('未保存更改');
  }, []);

  const undo = useCallback((): void => {
    setHistory((items) => {
      const previous = items.at(-1);
      if (!previous) return items;
      setFuture((itemsFuture) => [pageRef.current, ...itemsFuture].slice(0, MAX_HISTORY));
      setPage(previous);
      setNotice('已撤销');
      return items.slice(0, -1);
    });
  }, []);

  const redo = useCallback((): void => {
    setFuture((items) => {
      const next = items[0];
      if (!next) return items;
      setHistory((itemsHistory) => [...itemsHistory, pageRef.current].slice(-MAX_HISTORY));
      setPage(next);
      setNotice('已重做');
      return items.slice(1);
    });
  }, []);

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent): void => {
      if (!(event.ctrlKey || event.metaKey)) return;
      if (event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
      }
      if (event.key.toLowerCase() === 'y') {
        event.preventDefault();
        redo();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [redo, undo]);

  const addComponent = (type: StoreComponentType): void => {
    const component: StoreComponentSchema = {
      id: `${type.toLowerCase()}-${Date.now()}`,
      type,
      props: {},
      style: {},
    };
    updatePage((current) => ({ ...current, components: [...current.components, component] }));
    setSelectedId(component.id);
  };

  const removeSelected = (): void => {
    if (!selectedId) return;
    updatePage((current) => ({
      ...current,
      components: current.components.filter((component) => component.id !== selectedId),
    }));
    setSelectedId(null);
  };

  const duplicateSelected = (): void => {
    if (!selected) return;
    const copy: StoreComponentSchema = {
      ...selected,
      id: `${selected.type.toLowerCase()}-${Date.now()}`,
    };
    updatePage((current) => {
      const index = current.components.findIndex((component) => component.id === selected.id);
      const components = [...current.components];
      components.splice(index + 1, 0, copy);
      return { ...current, components };
    });
    setSelectedId(copy.id);
  };

  const moveSelected = (direction: -1 | 1): void => {
    if (!selectedId) return;
    updatePage((current) => {
      const index = current.components.findIndex((component) => component.id === selectedId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= current.components.length) return current;
      const components = [...current.components];
      [components[index], components[target]] = [components[target], components[index]];
      return { ...current, components };
    });
  };

  const save = async (): Promise<void> => {
    try {
      const saved = await saveManagedPage(pageRef.current);
      setPage(saved);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
      setNotice(`已保存 v${saved.version}`);
    } catch {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(pageRef.current));
      setNotice('接口暂不可用，已保存到本地草稿');
    }
  };
  const [runSave, saving] = useDebounceAction(save, 1000);
  const publish = async (): Promise<void> => {
    try {
      const published = await publishManagedPage(pageRef.current.id);
      setPage(published);
      setNotice('官网页面已发布');
    } catch {
      setNotice('仅官网页面可发布，或当前接口暂不可用');
    }
  };
  const [runPublish, publishing] = useDebounceAction(publish, 800);

  const applyTemplate = (components: StoreComponentSchema[]): void => {
    updatePage((current) => ({
      ...current,
      components: components.map((component) => ({
        ...component,
        id: `${component.type.toLowerCase()}-${Date.now()}-${Math.random()}`,
      })),
    }));
    setSelectedId(null);
  };

  const updateSelectedProp = (key: string, value: string): void => {
    if (!selected) return;
    updatePage((current) => ({
      ...current,
      components: current.components.map((component) =>
        component.id === selected.id
          ? { ...component, props: { ...component.props, [key]: value } }
          : component,
      ),
    }));
  };

  const updateSelectedStyle = (key: string, value: string): void => {
    if (!selected) return;
    updatePage((current) => ({
      ...current,
      components: current.components.map((component) =>
        component.id === selected.id
          ? { ...component, style: { ...component.style, [key]: value } }
          : component,
      ),
    }));
  };

  const handleDrop = (event: React.DragEvent<HTMLElement>): void => {
    event.preventDefault();
    const type = event.dataTransfer.getData(
      'application/x-liteshop-component',
    ) as StoreComponentType;
    if (COMPONENT_GROUPS.some((group) => group.types.includes(type))) addComponent(type);
  };

  const handleCanvasKeyDown = (event: ReactKeyboardEvent<HTMLElement>): void => {
    if (event.key === 'Delete' && selectedId) {
      event.preventDefault();
      removeSelected();
    }
  };

  return (
    <div className="editor-page builder-page" onKeyDown={handleCanvasKeyDown}>
      <header className="builder-toolbar">
        <div>
          <p>商城装修</p>
          <h1>首页搭建器</h1>
        </div>
        <div className="builder-toolbar__actions" aria-label="搭建器工具">
          <button className="ghost-button" type="button" disabled={!history.length} onClick={undo}>
            撤销
          </button>
          <button className="ghost-button" type="button" disabled={!future.length} onClick={redo}>
            重做
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() => setZoom((value) => (value >= 1 ? 0.75 : value + 0.25))}
          >
            缩放 {Math.round(zoom * 100)}%
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={saving}
            onClick={() => void runSave()}
          >
            {saving ? '保存中…' : '保存'}
          </button>
          <button
            className="primary-action"
            type="button"
            disabled={publishing}
            onClick={() => void runPublish()}
          >
            {publishing ? '发布中…' : '发布官网页'}
          </button>
        </div>
      </header>
      <p className="list-status" role="status" aria-live="polite">
        {notice}
      </p>
      <div className="builder-layout">
        <aside className="panel builder-library" aria-label="组件库">
          <div className="panel-title">
            <h2>组件库</h2>
            <span>{COMPONENT_GROUPS.flatMap((group) => group.types).length} 个组件</span>
          </div>
          {COMPONENT_GROUPS.map((group) => (
            <section className="builder-library__group" key={group.label}>
              <h3>{group.label}</h3>
              <div className="builder-library__items">
                {group.types.map((type) => (
                  <button
                    className="builder-library__item"
                    draggable
                    type="button"
                    key={type}
                    onDragStart={(event) =>
                      event.dataTransfer.setData('application/x-liteshop-component', type)
                    }
                    onClick={() => addComponent(type)}
                  >
                    <span>{componentLabel(type)}</span>
                    <small>{type}</small>
                  </button>
                ))}
              </div>
            </section>
          ))}
          <div className="builder-templates">
            <h3>页面模板</h3>
            {TEMPLATES.map((template) => (
              <button
                className="ghost-button"
                type="button"
                key={template.key}
                onClick={() => applyTemplate(template.components)}
              >
                {template.label}
              </button>
            ))}
          </div>
        </aside>
        <main className="builder-canvas-wrap" aria-label="页面画布">
          <div className="builder-canvas-wrap__bar">
            <label>
              页面
              <select
                value={page.id}
                onChange={(event) =>
                  setPage((current) => ({ ...current, id: Number(event.target.value) }))
                }
              >
                {pages.map((item) => (
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
                setNotice(
                  openPreview(pageRef.current)
                    ? '已打开 H5 草稿预览'
                    : '浏览器阻止了预览窗口，请允许弹窗后重试',
                )
              }
            >
              预览
            </button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                void copyManagedPage(page.id, {
                  slug: `${page.slug}-copy`,
                  name: `${page.name ?? page.slug} 副本`,
                })
                  .then((copied) => setNotice(`已复制为 /${copied.slug}`))
                  .catch(() => setNotice('复制需要连接后台接口'));
              }}
            >
              复制页面
            </button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                void setManagedHome(page.id)
                  .then(() => setNotice('已设为首页'))
                  .catch(() => setNotice('设置首页需要连接后台接口'));
              }}
            >
              设为首页
            </button>
          </div>
          <div
            className="builder-canvas"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            style={{ transform: `scale(${zoom})` }}
          >
            {page.components.length ? (
              page.components.map((component, index) => (
                <article
                  className={
                    component.id === selectedId
                      ? 'builder-item builder-item--selected'
                      : 'builder-item'
                  }
                  key={component.id}
                  tabIndex={0}
                  onClick={() => setSelectedId(component.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') setSelectedId(component.id);
                  }}
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
                          moveSelected(-1);
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
                          moveSelected(1);
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
                          duplicateSelected();
                        }}
                      >
                        复制
                      </button>
                      <button
                        className="danger-button"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          removeSelected();
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
                  value={String(
                    selected.props.title ?? selected.props.text ?? selected.props.placeholder ?? '',
                  )}
                  onChange={(event) =>
                    updateSelectedProp(
                      selected.type === 'RichText'
                        ? 'text'
                        : selected.type === 'SearchBar'
                          ? 'placeholder'
                          : 'title',
                      event.target.value,
                    )
                  }
                />
              </label>
              <label className="builder-field">
                背景 Token
                <select
                  value={selected.style.backgroundColor ?? ''}
                  onChange={(event) => updateSelectedStyle('backgroundColor', event.target.value)}
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
                  onChange={(event) => updateSelectedStyle('borderRadius', event.target.value)}
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
                  onChange={(event) => updateSelectedStyle('padding', event.target.value)}
                >
                  <option value="">默认间距</option>
                  <option value="var(--spacing-3)">紧凑</option>
                  <option value="var(--spacing-4)">标准</option>
                  <option value="var(--spacing-5)">宽松</option>
                </select>
              </label>
            </>
          ) : (
            <p className="feedback">选择画布中的组件开始编辑。</p>
          )}
        </aside>
      </div>
    </div>
  );
}
