import { useQuery } from '@tanstack/react-query';
import type { StoreComponentSchema, StorePageSchema } from '@liteshop/shared-types';
import { isRecoverableApiError } from '../../../service/http';
import { getStoreHomePage } from '../../../service/pages';
import { defaultStoreHomePage } from '../model/home-config';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function normalizeStyle(value: unknown): Record<string, string> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(
      (entry): entry is [string, string] => typeof entry[1] === 'string',
    ),
  );
}

export function normalizeStoreHomePage(schema: StorePageSchema): StorePageSchema {
  const rawComponents: unknown = schema?.components;
  if (!Array.isArray(rawComponents)) return { ...schema, components: [] };
  const usedIds = new Set<string>();

  return {
    ...schema,
    pageStyle: normalizeStyle(schema.pageStyle),
    components: rawComponents.flatMap((value, index): StoreComponentSchema[] => {
      if (!isRecord(value) || typeof value.type !== 'string' || !value.type) return [];
      const baseId =
        typeof value.id === 'string' && value.id
          ? value.id
          : `${value.type.toLowerCase()}-${index + 1}`;
      let id = baseId;
      let suffix = 2;
      while (usedIds.has(id)) {
        id = `${baseId}-${suffix}`;
        suffix += 1;
      }
      usedIds.add(id);
      const animation =
        isRecord(value.animation) &&
        typeof value.animation.enabled === 'boolean' &&
        typeof value.animation.type === 'string'
          ? { enabled: value.animation.enabled, type: value.animation.type }
          : undefined;
      return [
        {
          id,
          type: value.type as StoreComponentSchema['type'],
          props: isRecord(value.props) ? value.props : {},
          style: normalizeStyle(value.style),
          ...(animation ? { animation } : {}),
        },
      ];
    }),
  };
}

/** 商城首页 Schema 查询，页面只负责编排渲染结果。 */
export function useStoreHomePageQuery() {
  return useQuery<StorePageSchema>({
    queryKey: ['store-page', 'home'],
    queryFn: async () => {
      try {
        const schema = await getStoreHomePage();
        return Array.isArray(schema?.components) && schema.components.length > 0
          ? normalizeStoreHomePage(schema)
          : defaultStoreHomePage;
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return defaultStoreHomePage;
      }
    },
  });
}
