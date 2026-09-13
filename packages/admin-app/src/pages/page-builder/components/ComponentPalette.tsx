import type { JSX } from 'react';
import type { StoreComponentType } from '@liteshop/shared-types';
import type { ComponentGroup, PageTemplate } from '../model/page-builder-model';
import { componentLabel } from '../model/page-builder-model';

interface ComponentPaletteProps {
  channel: 'store' | 'site';
  componentGroups: ComponentGroup[];
  pageTemplates: PageTemplate[];
  onChannelChange: (channel: 'store' | 'site') => void;
  onAddComponent: (type: StoreComponentType) => void;
  onApplyTemplate: (components: PageTemplate['components']) => void;
}

/** 搭建器左侧模式切换、组件库与模板列表。 */
export function ComponentPalette({
  channel,
  componentGroups,
  pageTemplates,
  onChannelChange,
  onAddComponent,
  onApplyTemplate,
}: ComponentPaletteProps): JSX.Element {
  return (
    <aside className="panel builder-library" aria-label="组件库">
      <div className="builder-mode-switch" role="group" aria-label="编辑模式">
        <button
          className={channel === 'store' ? 'selected' : ''}
          type="button"
          aria-pressed={channel === 'store'}
          onClick={() => onChannelChange('store')}
        >
          商城 375px
        </button>
        <button
          className={channel === 'site' ? 'selected' : ''}
          type="button"
          aria-pressed={channel === 'site'}
          onClick={() => onChannelChange('site')}
        >
          官网 1200px
        </button>
      </div>
      <div className="panel-title">
        <h2>组件库</h2>
        <span>{componentGroups.flatMap((group) => group.types).length} 个组件</span>
      </div>
      {componentGroups.map((group) => (
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
                onClick={() => onAddComponent(type)}
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
        {pageTemplates.map((template) => (
          <button
            className="ghost-button"
            type="button"
            key={template.key}
            onClick={() => onApplyTemplate(template.components)}
          >
            {template.label}
          </button>
        ))}
      </div>
    </aside>
  );
}
