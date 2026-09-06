import type { JSX } from 'react';
import { useMemo, useState } from 'react';
import type { StoreComponentSchema } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';

const componentTypes: StoreComponentSchema['type'][] = [
  'SearchBar',
  'Carousel',
  'CategoryGrid',
  'ProductGrid',
  'ActivityBanner',
  'Tabbar',
];

/** 商城页面搭建器基础版，支持添加、排序、删除和撤销。 */
export function PageBuilderPage(): JSX.Element {
  const [components, setComponents] = useState<StoreComponentSchema[]>([]);
  const [history, setHistory] = useState<StoreComponentSchema[][]>([]);
  const schema = useMemo(() => ({ version: 1, components }), [components]);
  const update = (next: StoreComponentSchema[]) => {
    setHistory((current) => [...current.slice(-49), components]);
    setComponents(next);
  };
  const [runUpdate, updating] = useDebounceAction(update, 300);
  const undo = (): void => {
    const previous = history.at(-1);
    if (!previous) return;
    setHistory((current) => current.slice(0, -1));
    setComponents(previous);
  };
  const [runUndo, undoing] = useDebounceAction(undo, 300);
  const addComponent = (type: StoreComponentSchema['type']): void => {
    void runUpdate([...components, { id: `${type}-${Date.now()}`, type, props: {}, style: {} }]);
  };
  const removeComponent = (componentId: string): void => {
    void runUpdate(components.filter((item) => item.id !== componentId));
  };
  const moveUp = (index: number): void => {
    if (index === 0) return;
    const next = [...components];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    void runUpdate(next);
  };
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>商城装修</p>
          <h1>首页搭建器</h1>
        </div>
        <button
          type="button"
          disabled={!history.length || undoing || updating}
          onClick={() => void runUndo()}
        >
          撤销
        </button>
      </header>
      <div className="builder-layout">
        <aside className="panel">
          <h2>组件</h2>
          {componentTypes.map((type) => (
            <button
              type="button"
              key={type}
              disabled={updating || undoing}
              onClick={() => addComponent(type)}
            >
              {type}
            </button>
          ))}
        </aside>
        <main className="panel" aria-label="页面预览">
          {schema.components.length ? (
            schema.components.map((component, index) => (
              <article className="builder-item" key={component.id}>
                <span>{component.type}</span>
                <button
                  type="button"
                  disabled={updating || undoing}
                  onClick={() => removeComponent(component.id)}
                >
                  删除
                </button>
                <button
                  type="button"
                  disabled={index === 0 || updating || undoing}
                  onClick={() => moveUp(index)}
                >
                  上移
                </button>
              </article>
            ))
          ) : (
            <p className="feedback">从左侧添加组件开始</p>
          )}
        </main>
      </div>
    </div>
  );
}
