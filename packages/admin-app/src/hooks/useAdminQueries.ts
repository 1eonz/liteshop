import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { OrderStatus, ProductStatus } from '@liteshop/shared-types';
import type {
  AdminPermission,
  AdminRole,
  AuditLogEntry,
  CategorySummary,
  FreightTemplate,
  InventoryLedgerEntry,
  InventoryRow,
  MemberDetail,
  MemberSummary,
  OrderDetail,
  PageResponse,
  ProductDetailResponse,
  ProductSummary,
} from '@liteshop/shared-types';
import {
  cancelAdminOrder,
  adjustInventory,
  changeAdminOrderPrice,
  createAdminCategory,
  createAdminProduct,
  deleteAdminCategory,
  getAdminProduct,
  getDashboard,
  listAdminCategories,
  listAdminPermissions,
  listAdminRoles,
  listAuditLogs,
  listFreightTemplates,
  listInventory,
  listMembers,
  getMember,
  updateMemberTags,
  updateMemberLevel,
  listInventoryLedger,
  listAdminOrders,
  listAdminProducts,
  shipAdminOrder,
  updateAdminCategory,
  updateAdminOrder,
  updateAdminProduct,
  type OrderManagementInput,
  type ProductCreateInput,
  type ProductUpdateInput,
  type ShipOrderInput,
} from '../service/admin';
import { isRecoverableApiError } from '../service/http';

const demoProducts: ProductSummary[] = [
  {
    id: 1,
    name: '晨雾保温杯',
    coverUrl: '',
    minPrice: 12900,
    maxPrice: 12900,
    salesCount: 128,
    status: ProductStatus.ON_SHELF,
  },
  {
    id: 2,
    name: '云朵卫衣',
    coverUrl: '',
    minPrice: 26900,
    maxPrice: 26900,
    salesCount: 96,
    status: ProductStatus.ON_SHELF,
  },
];

const demoOrders: PageResponse<OrderDetail> = {
  items: [
    {
      id: 1,
      orderNo: 'LS202609050001',
      status: OrderStatus.PAID,
      totalAmount: 12900,
      productAmount: 12900,
      freightAmount: 0,
      discountAmount: 0,
      refundStatus: 'NONE',
      paidAmount: 12900,
      paidAt: '2026-09-05T08:00:00+08:00',
      shippedAt: null,
      completedAt: null,
      cancelledAt: null,
      cancelReason: null,
      addressSnapshot: {
        receiverName: '张三',
        detail: '杭州市西湖区文三路 1 号',
      },
      remark: '',
      shippingCompanyCode: '',
      trackingNo: '',
      items: [
        {
          id: 1,
          skuId: 1,
          productId: 1,
          productName: '晨雾保温杯',
          skuCode: 'CUP-480',
          skuName: '480ml',
          specValues: { 容量: '480ml' },
          productImage: '',
          quantity: 1,
          priceCents: 12900,
          weightGrams: 420,
          discountAmount: 0,
          totalAmount: 12900,
        },
      ],
      createdAt: '2026-09-05T08:00:00+08:00',
    },
  ],
  meta: { page: 1, pageSize: 20, total: 1, hasNext: false },
};
const demoInventory: PageResponse<InventoryRow> = {
  items: [
    {
      skuId: 1,
      skuCode: 'CUP-480',
      name: '晨雾保温杯 / 标准款',
      physicalStock: 100,
      availableStock: 96,
      lockedStock: 4,
      safetyStock: 10,
      warning: false,
    },
    {
      skuId: 2,
      skuCode: 'HOODIE-M',
      name: '云朵卫衣 / M',
      physicalStock: 58,
      availableStock: 56,
      lockedStock: 2,
      safetyStock: 60,
      warning: true,
    },
  ],
  meta: { page: 1, pageSize: 50, total: 2, hasNext: false },
};
/** 后台商品查询，开发 API 不可用时保留可浏览的本地快照。 */
export function useAdminProductsQuery(query: { q?: string } = {}) {
  return useQuery({
    queryKey: ['admin-products', query],
    queryFn: async () => {
      try {
        return await listAdminProducts(query);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        const items = query.q
          ? demoProducts.filter((product) => product.name.includes(query.q ?? ''))
          : demoProducts;
        return {
          items,
          meta: { page: 1, pageSize: 20, total: items.length, hasNext: false },
        };
      }
    },
  });
}

/** 后台商品详情查询，接口不可用时沿用同一套演示商品快照。 */
export function useAdminProductQuery(productId: number | null) {
  return useQuery<ProductDetailResponse>({
    queryKey: ['admin-product', productId],
    queryFn: async () => {
      if (productId === null) throw new Error('商品 ID 无效');
      try {
        return await getAdminProduct(productId);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        const product = demoProducts.find((item) => item.id === productId);
        if (!product) throw error;
        return {
          ...product,
          subtitle: '轻盈材质，适合每日通勤',
          brand: 'LiteShop',
          description: '食品级材质，简洁耐用，支持全天候生活场景。',
          detailHtml: '',
          detailImages: [],
          seoTitle: null,
          seoDescription: null,
          seoKeywords: null,
          specDefinitions: [
            {
              id: 1,
              name: '容量',
              sortOrder: 0,
              values: [{ id: 1, value: '480ml', sortOrder: 0 }],
            },
          ],
          skus: [
            {
              skuId: product.id,
              skuCode: `DEMO-${product.id}`,
              name: '标准款',
              priceCents: product.minPrice,
              quantity: 100,
              specs: { 容量: '480ml' },
            },
          ],
        };
      }
    },
    enabled: productId !== null,
  });
}

/** 后台商品创建 mutation，成功后缓存详情并刷新列表。 */
export function useCreateAdminProductMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProductCreateInput) => createAdminProduct(input),
    retry: 0,
    onSuccess: (product) => {
      queryClient.setQueryData(['admin-product', product.id], product);
      void queryClient.invalidateQueries({ queryKey: ['admin-products'] });
    },
  });
}

/** 后台商品更新 mutation，成功后同步详情和列表缓存。 */
export function useUpdateAdminProductMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, input }: { productId: number; input: ProductUpdateInput }) =>
      updateAdminProduct(productId, input),
    retry: 0,
    onSuccess: (product, variables) => {
      queryClient.setQueryData(['admin-product', variables.productId], product);
      void queryClient.invalidateQueries({ queryKey: ['admin-products'] });
    },
  });
}

/** 后台订单查询。 */
export function useAdminOrdersQuery() {
  return useQuery({
    queryKey: ['admin-orders'],
    queryFn: async () => {
      try {
        return await listAdminOrders();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoOrders;
      }
    },
  });
}

/** 后台库存查询。 */
export function useInventoryQuery() {
  return useQuery({
    queryKey: ['admin-inventory'],
    queryFn: async () => {
      try {
        return await listInventory();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoInventory;
      }
    },
  });
}

/** 后台看板聚合查询。 */
export function useDashboardQuery() {
  return useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: getDashboard,
  });
}

/** 运费模板查询。 */
export function useFreightTemplatesQuery() {
  return useQuery<FreightTemplate[]>({
    queryKey: ['admin-freight-templates'],
    queryFn: async () => {
      try {
        return await listFreightTemplates();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
}

/** 后台发货 mutation，复用服务端订单状态机。 */
export function useShipAdminOrderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, input }: { orderId: number; input: ShipOrderInput }) =>
      shipAdminOrder(orderId, input),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
    },
  });
}

/** 后台库存调整 mutation，成功后刷新库存台账和看板。 */
export function useAdjustInventoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      skuId,
      quantity,
      reason,
    }: {
      skuId: number;
      quantity: number;
      reason: string;
    }) => adjustInventory(skuId, quantity, reason),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-inventory'] });
      void queryClient.invalidateQueries({ queryKey: ['admin-dashboard'] });
    },
  });
}

/** 后台分类查询。 */
export function useAdminCategoriesQuery() {
  return useQuery<CategorySummary[]>({
    queryKey: ['admin-categories'],
    queryFn: async () => {
      try {
        return await listAdminCategories();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
}

/** 后台分类新增、编辑和停用动作。 */
export function useAdminCategoryMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-categories'] });
  };
  return {
    create: useMutation({
      mutationFn: createAdminCategory,
      retry: 0,
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({
        categoryId,
        input,
      }: {
        categoryId: number;
        input: Partial<CategorySummary>;
      }) => updateAdminCategory(categoryId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: deleteAdminCategory,
      retry: 0,
      onSuccess: refresh,
    }),
  };
}

/** 后台订单取消和备注地址编辑动作。 */
export function useAdminOrderMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
  };
  return {
    cancel: useMutation({
      mutationFn: cancelAdminOrder,
      retry: 0,
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({ orderId, input }: { orderId: number; input: OrderManagementInput }) =>
        updateAdminOrder(orderId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    changePrice: useMutation({
      mutationFn: ({ orderId, totalAmount }: { orderId: number; totalAmount: number }) =>
        changeAdminOrderPrice(orderId, totalAmount),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}

/** 后台操作日志查询。 */
export function useAuditLogsQuery() {
  return useQuery<AuditLogEntry[]>({
    queryKey: ['admin-audit-logs'],
    queryFn: async () => {
      try {
        return await listAuditLogs();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
}

/** 后台 RBAC 角色和权限查询。 */
export function useRbacQuery() {
  const roles = useQuery<AdminRole[]>({
    queryKey: ['admin-roles'],
    queryFn: async () => {
      try {
        return await listAdminRoles();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
  const permissions = useQuery<AdminPermission[]>({
    queryKey: ['admin-permissions'],
    queryFn: async () => {
      try {
        return await listAdminPermissions();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
  return { roles, permissions };
}

/** 指定 SKU 库存流水查询。 */
export function useInventoryLedgerQuery(skuId: number | null) {
  return useQuery<InventoryLedgerEntry[]>({
    queryKey: ['inventory-ledger', skuId],
    enabled: skuId !== null,
    queryFn: () => listInventoryLedger(skuId as number),
  });
}

/** 后台会员列表，失败时显示真实错误，不使用演示数据替代。 */
export function useMembersQuery() {
  return useQuery<PageResponse<MemberSummary>>({
    queryKey: ['admin-members'],
    queryFn: () => listMembers(),
  });
}

/** 后台会员详情。 */
export function useMemberQuery(userId: number | null) {
  return useQuery<MemberDetail>({
    queryKey: ['admin-member', userId],
    queryFn: () => getMember(userId as number),
    enabled: userId !== null,
  });
}

/** 后台会员标签和等级更新。 */
export function useMemberMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-members'] });
  };
  return {
    updateTags: useMutation({
      mutationFn: ({ userId, tags }: { userId: number; tags: string[] }) =>
        updateMemberTags(userId, tags),
      retry: 0,
      onSuccess: refresh,
    }),
    updateLevel: useMutation({
      mutationFn: ({ userId, memberLevel }: { userId: number; memberLevel: 'NORMAL' | 'MEMBER' }) =>
        updateMemberLevel(userId, memberLevel),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}
