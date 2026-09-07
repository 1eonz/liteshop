import type { FreightTemplate } from '@liteshop/shared-types';
import type { JSX } from 'react';
import { useCallback, useState } from 'react';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import {
  useFreightTemplateMutations,
  useFreightTemplatesQuery,
} from '../../features/inventory';
import type { FreightTemplateInput } from '../../service/admin/inventory';
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
  firstUnit: string;
  firstFee: string;
  additionalUnit: string;
  additionalFee: string;
}

const emptyDraft: TemplateDraft = {
  name: '',
  type: 'PIECE',
  isDefault: false,
  enabled: true,
  firstUnit: '1',
  firstFee: '0',
  additionalUnit: '1',
  additionalFee: '0',
};

function draftFromTemplate(template: FreightTemplate): TemplateDraft {
  const item = template.items[0];
  return {
    name: template.name,
    type: template.type,
    isDefault: template.isDefault,
    enabled: template.enabled,
    firstUnit: item?.firstUnit ?? '1',
    firstFee: String(item?.firstFee ?? 0),
    additionalUnit: item?.additionalUnit ?? '1',
    additionalFee: String(item?.additionalFee ?? 0),
  };
}

function toInput(draft: TemplateDraft): FreightTemplateInput | null {
  const firstUnit = Number(draft.firstUnit);
  const firstFee = Number(draft.firstFee);
  const additionalUnit = Number(draft.additionalUnit);
  const additionalFee = Number(draft.additionalFee);
  if (
    !draft.name.trim() ||
    !Number.isFinite(firstUnit) ||
    firstUnit <= 0 ||
    !Number.isInteger(firstFee) ||
    firstFee < 0 ||
    !Number.isFinite(additionalUnit) ||
    additionalUnit <= 0 ||
    !Number.isInteger(additionalFee) ||
    additionalFee < 0
  ) {
    return null;
  }
  return {
    name: draft.name.trim(),
    type: draft.type,
    isDefault: draft.isDefault,
    enabled: draft.enabled,
    items: [
      {
        regionCodes: [],
        firstUnit,
        firstFee,
        additionalUnit,
        additionalFee,
      },
    ],
  };
}

/** 运费模板管理：覆盖列表、新建、编辑、复制、启停和删除。 */
export function FreightTemplatesPage(): JSX.Element {
  const templatesQuery = useFreightTemplatesQuery();
  const mutations = useFreightTemplateMutations();
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
        await mutations.create.mutateAsync(input);
      } else {
        await mutations.update.mutateAsync({ templateId: editingId, input });
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
        await mutations.create.mutateAsync({ ...input, isDefault: false });
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
        <ErrorState onRetry={() => void templatesQuery.refetch()}>运费模板加载失败，请重试。</ErrorState>
      </div>
    );
  }

  const templates = templatesQuery.data ?? [];
  return (
    <div className="editor-page freight-page">
      <header>
        <div>
          <p>物流与计费</p>
          <h1>运费模板</h1>
        </div>
        <button type="button" disabled={templatesQuery.isFetching} onClick={() => void templatesQuery.refetch()}>
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
                  <span className={template.enabled ? 'status-badge status-badge--on' : 'status-badge'}>
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

        <section className="editor-form freight-editor" aria-label={editingId === null ? '新建运费模板' : '编辑运费模板'}>
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
                onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
              />
            </label>
            <label>
              计费方式
              <select
                value={draft.type}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, type: event.target.value as FreightTemplate['type'] }))
                }
              >
                <option value="PIECE">按件计费</option>
                <option value="WEIGHT">按重量计费</option>
                <option value="REGION">按地区计费</option>
              </select>
            </label>
            <label>
              首段数量
              <input
                inputMode="decimal"
                value={draft.firstUnit}
                onChange={(event) => setDraft((current) => ({ ...current, firstUnit: event.target.value }))}
              />
            </label>
            <label>
              首段费用（分）
              <input
                inputMode="numeric"
                value={draft.firstFee}
                onChange={(event) => setDraft((current) => ({ ...current, firstFee: event.target.value }))}
              />
            </label>
            <label>
              续段数量
              <input
                inputMode="decimal"
                value={draft.additionalUnit}
                onChange={(event) => setDraft((current) => ({ ...current, additionalUnit: event.target.value }))}
              />
            </label>
            <label>
              续段费用（分）
              <input
                inputMode="numeric"
                value={draft.additionalFee}
                onChange={(event) => setDraft((current) => ({ ...current, additionalFee: event.target.value }))}
              />
            </label>
          </div>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={draft.isDefault}
              onChange={(event) => setDraft((current) => ({ ...current, isDefault: event.target.checked }))}
            />
            设为默认模板
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => setDraft((current) => ({ ...current, enabled: event.target.checked }))}
            />
            保存后启用
          </label>
          <p className="muted freight-help">金额统一使用整数分；地区计费项可在后续编辑中按省份扩展。</p>
          <button type="button" disabled={saving} onClick={() => void runSave()}>
            {saving ? '保存中…' : editingId === null ? '创建模板' : '保存修改'}
          </button>
        </section>
      </div>
    </div>
  );
}

