import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { FreightTemplate } from '@liteshop/shared-types';
import {
  createFreightTemplate,
  deleteFreightTemplate,
  listFreightTemplates,
  addFreightTemplateItem,
  updateFreightTemplateItem,
  updateFreightTemplate,
  type FreightTemplateInput,
  type FreightTemplateItemInput,
} from '../../../service/admin/inventory';
import { isRecoverableApiError } from '../../../service/http';

const demoFreightTemplates: FreightTemplate[] = [
  {
    id: 1,
    name: '全国包邮模板',
    type: 'PIECE',
    isDefault: true,
    enabled: true,
    items: [
      {
        id: 1,
        regionCodes: [],
        firstUnit: '1',
        firstFee: 0,
        additionalUnit: '1',
        additionalFee: 0,
        freeCondition: null,
      },
    ],
    createdAt: '2026-09-01T08:00:00+08:00',
    updatedAt: '2026-09-01T08:00:00+08:00',
  },
];

/** 后台运费模板列表查询，开发环境仅在服务不可用时提供演示快照。 */
export function useFreightTemplatesQuery() {
  return useQuery({
    queryKey: ['admin-freight-templates'],
    queryFn: async () => {
      try {
        return await listFreightTemplates();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoFreightTemplates;
      }
    },
  });
}

/** 运费模板写操作，所有 mutation 禁止自动重试，避免重复写入。 */
export function useFreightTemplateMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-freight-templates'] });
  };
  return {
    create: useMutation({
      mutationFn: (input: FreightTemplateInput) => createFreightTemplate(input),
      retry: 0,
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({ templateId, input }: { templateId: number; input: Partial<FreightTemplateInput> }) =>
        updateFreightTemplate(templateId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: (templateId: number) => deleteFreightTemplate(templateId),
      retry: 0,
      onSuccess: refresh,
    }),
    addItem: useMutation({
      mutationFn: ({ templateId, input }: { templateId: number; input: FreightTemplateItemInput }) =>
        addFreightTemplateItem(templateId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    updateItem: useMutation({
      mutationFn: ({
        templateId,
        itemId,
        input,
      }: {
        templateId: number;
        itemId: number;
        input: Partial<FreightTemplateItemInput>;
      }) => updateFreightTemplateItem(templateId, itemId, input),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}
