import type { FreightTemplate } from '@liteshop/shared-types';
import type { JSX } from 'react';
import { useCallback, useState } from 'react';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useFreightTemplateMutations, useFreightTemplatesQuery } from '../../features/inventory';
import type { FreightTemplateInput, FreightTemplateItemInput } from '../../service/admin/inventory';
import { useDebounceAction } from '../../hooks';

const typeLabels: Record<FreightTemplate['type'], string> = {
  PIECE: '按件计费',
  WEIGHT: '按重量计费',
  REGION: '按地区计费',
};

interface TemplateDraft {
  name: string;
  type: FreightTemplate['type'];
  isDefault: boolean;
  enabled: boolean;
  items: TemplateItemDraft[];
}

interface TemplateItemDraft {
  id?: number;
  firstUnit: string;
  firstFee: string;
  additionalUnit: string;
  additionalFee: string;
  regionCodes: string;
}

const emptyItem: TemplateItemDraft = {
  firstUnit: '1',
  firstFee: '0',
  additionalUnit: '1',
  additionalFee: '0',
  regionCodes: '',
};

const emptyDraft: TemplateDraft = {
  name: '',
  type: 'PIECE',
  isDefault: false,
  enabled: true,
  items: [{ ...emptyItem }],
};

function draftFromTemplate(template: FreightTemplate): TemplateDraft {
  return {
    name: template.name,
    type: template.type,
    isDefault: template.isDefault,
    enabled: template.enabled,
    items: template.items.length
      ? template.items.map((item) => ({
          id: item.id,
          firstUnit: item.firstUnit,
          firstFee: String(item.firstFee),
          additionalUnit: item.additionalUnit,
          additionalFee: String(item.additionalFee),
          regionCodes: item.regionCodes.join(', '),
        }))
      : [{ ...emptyItem }],
  };
}

interface FreightDraftInput {
  template: Omit<FreightTemplateInput, 'items'>;
  items: FreightTemplateItemInput[];
}

function toInput(draft: TemplateDraft): FreightDraftInput | null {
  if (!draft.name.trim() || !draft.items.length) return null;
  const items: FreightTemplateItemInput[] = [];
  for (const item of draft.items) {
    const firstUnit = Number(item.firstUnit);
    const firstFee = Number(item.firstFee);
    const additionalUnit = Number(item.additionalUnit);
    const additionalFee = Number(item.additionalFee);
    if (
      !Number.isFinite(firstUnit) ||
      firstUnit <= 0 ||
      !Number.isInteger(firstFee) ||
      firstFee < 0 ||
      !Number.isFinite(additionalUnit) ||
      additionalUnit <= 0 ||
      !Number.isInteger(additionalFee) ||
      additionalFee < 0
    )
      return null;
    items.push({
      regionCodes: item.regionCodes
        .split(',')
        .map((code) => code.trim())
        .filter(Boolean),
      firstUnit,
      firstFee,
      additionalUnit,
      additionalFee,
    });
  }
  return {
    template: {
      name: draft.name.trim(),
      type: draft.type,
      isDefault: draft.isDefault,
      enabled: draft.enabled,
    },
    items,
  };
}

/** 运费模板管理：覆盖列表、新建、编辑、复制、启停和删除。 */
export function FreightTemplatesPage(): JSX.Element {
  const templatesQuery = useFreightTemplatesQuery();
  const mutations = useFreightTemplateMutations();
  const templates = templatesQuery.data ?? [];
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<TemplateDraft>(emptyDraft);
  const [feedback, setFeedback] = useState('');

  const openCreate = useCallback(() => {
    setEditingId(null);
    setDraft(emptyDraft);
    setFeedback('');
  }, []);
  const openEdit = useCallback((template: FreightTemplate) => {
    setEditingId(template.id);
    setDraft(draftFromTemplate(template));
    setFeedback('');
  }, []);
  const save = useCallback(async () => {
    const input = toInput(draft);
    if (!input) {
      setFeedback('请填写有效的模板名称、计费单位和整数分金额。');
      return;
    }
    setFeedback('');
    try {
      if (editingId === null) {
        await mutations.create.mutateAsync({ ...input.template, items: input.items });
      } else {
        await mutations.update.mutateAsync({
          templateId: editingId,
          input: { ...input.template, items: input.items },
        });
      }
      openCreate();
    } catch {
      setFeedback('保存失败，请确认权限和模板状态后重试。');
    }
  }, [draft, editingId, mutations.create, mutations.update, openCreate]);
  const [runSave, saving] = useDebounceAction(save, 800);

  const toggle = useCallback(
    async (template: FreightTemplate) => {
      setFeedback('');
      try {
        await mutations.update.mutateAsync({
          templateId: template.id,
          input: { enabled: !template.enabled },
        });
      } catch {
        setFeedback('启停操作失败，请稍后重试。');
      }
    },
    [mutations.update],
  );
  const [runToggle, toggling] = useDebounceAction(toggle, 500);

  const remove = useCallback(
    async (template: FreightTemplate) => {
      if (!window.confirm(`确认删除运费模板“${template.name}”吗？`)) return;
      setFeedback('');
      try {
        await mutations.remove.mutateAsync(template.id);
        if (editingId === template.id) openCreate();
      } catch {
        setFeedback('删除失败，默认模板或已被商品使用的模板不可删除。');
      }
    },
    [editingId, mutations.remove, openCreate],
  );
  const [runRemove, removing] = useDebounceAction(remove, 500);

  const copy = useCallback(
    async (template: FreightTemplate) => {
      const input = toInput({ ...draftFromTemplate(template), name: `${template.name} 副本` });
      if (!input) return;
      setFeedback('');
      try {
        await mutations.create.mutateAsync({
          ...input.template,
          isDefault: false,
          items: input.items,
        });
      } catch {
        setFeedback('复制失败，请稍后重试。');
      }
    },
    [mutations.create],
  );
  const [runCopy, copying] = useDebounceAction(copy, 500);

  if (templatesQuery.isLoading) {
    return <FeedbackState>运费模板加载中…</FeedbackState>;
  }
  if (templatesQuery.isError) {
    return (
      <div className="editor-page">
        <ErrorState onRetry={() => void templatesQuery.refetch()}>
          运费模板加载失败，请重试。
        </ErrorState>
      </div>
    );
  }

  return (
    <div className="editor-page freight-page">
      <header>
        <div>
          <p>物流与计费</p>
          <h1>运费模板</h1>
        </div>
        <button
          type="button"
          disabled={templatesQuery.isFetching}
          onClick={() => void templatesQuery.refetch()}
        >
          {templatesQuery.isFetching ? '刷新中…' : '刷新'}
        </button>
      </header>
      {feedback && (
        <p className="feedback error-state" role="alert">
          {feedback}
        </p>
      )}
      <div className="freight-layout">
        <section className="editor-form freight-list" aria-label="运费模板列表">
          <div className="section-heading">
            <h2>模板列表</h2>
            <button type="button" onClick={openCreate}>
              新建模板
            </button>
          </div>
          {templates.length === 0 ? (
            <div className="feedback">暂无运费模板，请先创建一个模板。</div>
          ) : (
            templates.map((template) => (
              <article className="freight-row" key={template.id}>
                <div>
                  <strong>{template.name}</strong>
                  <span className="muted">
                    {typeLabels[template.type]} · {template.items.length} 个地区计费项
                  </span>
                </div>
                <div className="freight-row__status">
                  {template.isDefault && <span className="status-badge">默认</span>}
                  <span
                    className={template.enabled ? 'status-badge status-badge--on' : 'status-badge'}
                  >
                    {template.enabled ? '启用中' : '已停用'}
                  </span>
                </div>
                <div className="row-actions">
                  <button className="ghost-button" type="button" onClick={() => openEdit(template)}>
                    编辑
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    disabled={toggling}
                    onClick={() => void runToggle(template)}
                  >
                    {template.enabled ? '停用' : '启用'}
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    disabled={copying}
                    onClick={() => void runCopy(template)}
                  >
                    复制
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    disabled={removing}
                    onClick={() => void runRemove(template)}
                  >
                    删除
                  </button>
                </div>
              </article>
            ))
          )}
        </section>

        <section
          className="editor-form freight-editor"
          aria-label={editingId === null ? '新建运费模板' : '编辑运费模板'}
        >
          <div className="section-heading">
            <h2>{editingId === null ? '新建模板' : '编辑模板'}</h2>
            {editingId !== null && (
              <button className="ghost-button" type="button" onClick={openCreate}>
                取消编辑
              </button>
            )}
          </div>
          <div className="form-grid">
            <label>
              模板名称
              <input
                value={draft.name}
                maxLength={100}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label>
              计费方式
              <select
                value={draft.type}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    type: event.target.value as FreightTemplate['type'],
                  }))
                }
              >
                <option value="PIECE">按件计费</option>
                <option value="WEIGHT">按重量计费</option>
                <option value="REGION">按地区计费</option>
              </select>
            </label>
          </div>
          <div className="freight-items-editor">
            <div className="section-heading">
              <h3>地区计费项</h3>
              <button
                className="ghost-button"
                type="button"
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    items: [...current.items, { ...emptyItem }],
                  }))
                }
              >
                新增计费项
              </button>
            </div>
            {draft.items.map((item, index) => (
              <fieldset className="freight-item-editor" key={item.id ?? `new-${index}`}>
                <legend>计费项 {index + 1}</legend>
                <label>
                  地区编码（逗号分隔，空值为全国）
                  <input
                    value={item.regionCodes}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        items: current.items.map((currentItem, currentIndex) =>
                          currentIndex === index
                            ? { ...currentItem, regionCodes: event.target.value }
                            : currentItem,
                        ),
                      }))
                    }
                  />
                </label>
                <div className="form-grid">
                  {(
                    [
                      ['firstUnit', '首段数量', 'decimal'],
                      ['firstFee', '首段费用（分）', 'numeric'],
                      ['additionalUnit', '续段数量', 'decimal'],
                      ['additionalFee', '续段费用（分）', 'numeric'],
                    ] as const
                  ).map(([field, label, inputMode]) => (
                    <label key={field}>
                      {label}
                      <input
                        inputMode={inputMode}
                        value={item[field]}
                        onChange={(event) =>
                          setDraft((current) => ({
                            ...current,
                            items: current.items.map((currentItem, currentIndex) =>
                              currentIndex === index
                                ? { ...currentItem, [field]: event.target.value }
                                : currentItem,
                            ),
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
                <button
                  className="danger-button"
                  type="button"
                  disabled={draft.items.length === 1}
                  onClick={() =>
                    setDraft((current) => ({
                      ...current,
                      items: current.items.filter((_, currentIndex) => currentIndex !== index),
                    }))
                  }
                >
                  删除计费项
                </button>
              </fieldset>
            ))}
          </div>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={draft.isDefault}
              onChange={(event) =>
                setDraft((current) => ({ ...current, isDefault: event.target.checked }))
              }
            />
            设为默认模板
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, enabled: event.target.checked }))
              }
            />
            保存后启用
          </label>
          <p className="muted freight-help">
            金额统一使用整数分；每个地区计费项可单独配置首段和续段费用。
          </p>
          <button type="button" disabled={saving} onClick={() => void runSave()}>
            {saving ? '保存中…' : editingId === null ? '创建模板' : '保存修改'}
          </button>
        </section>
      </div>
    </div>
  );
}
