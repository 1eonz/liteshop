import type { JSX, KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { StoreComponentSchema, StoreComponentType } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import {
  COMPONENT_GROUPS,
  DEFAULT_PAGE,
  DEFAULT_SITE_PAGE,
  PAGE_BUILDER_MAX_HISTORY,
  PAGE_BUILDER_STORAGE_KEY,
  PAGE_TEMPLATES,
  SITE_COMPONENT_GROUPS,
  readPageDraft,
} from './model/page-builder-model';
import { BuilderCanvas } from './components/BuilderCanvas';
import { ComponentPalette } from './components/ComponentPalette';
import { PropsPanel } from './components/PropsPanel';
import { useAutoSave } from './hooks/useAutoSave';
import { usePageHistory } from './hooks/usePageHistory';
import {
  copyManagedPage,
  listManagedPages,
  publishManagedPage,
  saveManagedPage,
  setManagedHome,
} from '../../service/pages';

interface ManagedPage {
  id: number;
  slug: string;
  name: string;
  isHome: boolean;
  channel?: 'store' | 'site';
}

/** 商城低代码搭建器页面编排层，领域视图和历史逻辑分别由子模块负责。 */
export function PageBuilderPage(): JSX.Element {
  const [notice, setNotice] = useState('草稿已加载');
  const [channel, setChannel] = useState<'store' | 'site'>(
    () => readPageDraft().channel ?? 'store',
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pages, setPages] = useState<ManagedPage[]>([]);
  const [zoom, setZoom] = useState(1);
  const noticeRef = useRef(setNotice);
  noticeRef.current = setNotice;
  const showNotice = useCallback((message: string): void => noticeRef.current(message), []);
  const { page, setPage, pageRef, history, future, updatePage, undo, redo } = usePageHistory(
    readPageDraft,
    PAGE_BUILDER_MAX_HISTORY,
    showNotice,
  );
  const isSite = channel === 'site';
  const componentGroups = isSite ? SITE_COMPONENT_GROUPS : COMPONENT_GROUPS;
  const selected = useMemo(
    () => page.components.find((component) => component.id === selectedId) ?? null,
    [page.components, selectedId],
  );

  useAutoSave(pageRef, PAGE_BUILDER_STORAGE_KEY, () => showNotice('已自动保存草稿'));

  useEffect(() => {
    let active = true;
    void (async (): Promise<void> => {
      try {
        const items = await listManagedPages();
        if (active) setPages(items);
      } catch {
        if (active)
          setPages([{ id: 1, slug: 'home', name: '首页', isHome: true, channel: 'store' }]);
      }
    })();
    return () => {
      active = false;
    };
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

  const switchChannel = (nextChannel: 'store' | 'site'): void => {
    setChannel(nextChannel);
    setSelectedId(null);
    setPage((current) => {
      if (current.channel === nextChannel) return current;
      const fallback = nextChannel === 'site' ? DEFAULT_SITE_PAGE : DEFAULT_PAGE;
      return { ...fallback, id: current.id, channel: nextChannel };
    });
    showNotice(nextChannel === 'site' ? '已切换官网模式' : '已切换商城模式');
  };

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
      window.localStorage.setItem(PAGE_BUILDER_STORAGE_KEY, JSON.stringify(saved));
      showNotice(`已保存 v${saved.version}`);
    } catch {
      window.localStorage.setItem(PAGE_BUILDER_STORAGE_KEY, JSON.stringify(pageRef.current));
      showNotice('接口暂不可用，已保存到本地草稿');
    }
  };
  const [runSave, saving] = useDebounceAction(save, 1000);

  const publish = async (): Promise<void> => {
    try {
      const published = await publishManagedPage(pageRef.current.id);
      setPage(published);
      showNotice('官网页面已发布');
    } catch {
      showNotice('仅官网页面可发布，或当前接口暂不可用');
    }
  };
  const [runPublish, publishing] = useDebounceAction(publish, 800);

  const copyPage = useCallback(async (): Promise<void> => {
    try {
      const copied = await copyManagedPage(pageRef.current.id, {
        slug: `${pageRef.current.slug}-copy`,
        name: `${pageRef.current.name ?? pageRef.current.slug} 副本`,
      });
      showNotice(`已复制为 /${copied.slug}`);
    } catch {
      showNotice('复制需要连接后台接口');
    }
  }, [showNotice]);
  const [runCopyPage, copyingPage] = useDebounceAction(copyPage, 500);

  const setHome = useCallback(async (): Promise<void> => {
    try {
      await setManagedHome(pageRef.current.id);
      showNotice('已设为首页');
    } catch {
      showNotice('设置首页需要连接后台接口');
    }
  }, [showNotice]);
  const [runSetHome, settingHome] = useDebounceAction(setHome, 500);

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

  const updateAnimation = (type: string): void => {
    if (!selected) return;
    updatePage((current) => ({
      ...current,
      components: current.components.map((component) =>
        component.id === selected.id
          ? { ...component, animation: { enabled: type !== 'none', type } }
          : component,
      ),
    }));
  };

  const updateSeo = (key: 'title' | 'description', value: string): void => {
    updatePage((current) => ({ ...current, seo: { ...(current.seo ?? {}), [key]: value } }));
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
          <p>{isSite ? '官网内容管理' : '商城装修'}</p>
          <h1>{isSite ? '官网页面搭建器' : '商城首页搭建器'}</h1>
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
            disabled={!isSite || publishing}
            onClick={() => void runPublish()}
          >
            {publishing ? '发布中…' : isSite ? '发布官网页' : '商城页无需发布'}
          </button>
        </div>
      </header>
      <p className="list-status" role="status" aria-live="polite">
        {notice}
      </p>
      <div className="builder-layout">
        <ComponentPalette
          channel={channel}
          componentGroups={componentGroups}
          pageTemplates={PAGE_TEMPLATES}
          onChannelChange={switchChannel}
          onAddComponent={addComponent}
          onApplyTemplate={applyTemplate}
        />
        <BuilderCanvas
          page={page}
          pages={pages}
          selectedId={selectedId}
          zoom={zoom}
          isSite={isSite}
          copyingPage={copyingPage}
          settingHome={settingHome}
          componentTypes={componentGroups.flatMap((group) => group.types)}
          onPageChange={(id) => setPage((current) => ({ ...current, id }))}
          onSelect={setSelectedId}
          onDropComponent={addComponent}
          onMove={moveSelected}
          onDuplicate={duplicateSelected}
          onRemove={removeSelected}
          onPreviewNotice={showNotice}
          onCopyPage={() => void runCopyPage()}
          onSetHome={() => void runSetHome()}
        />
        <PropsPanel
          page={page}
          selected={selected}
          isSite={isSite}
          onPropChange={updateSelectedProp}
          onStyleChange={updateSelectedStyle}
          onAnimationChange={updateAnimation}
          onSeoChange={updateSeo}
        />
      </div>
    </div>
  );
}
