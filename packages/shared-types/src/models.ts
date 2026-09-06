import type { InventoryEventType, OrderStatus, PaymentProvider, ProductStatus } from './enums.js';

/** 统一接口响应信封。 */
export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  requestId: string;
}

export interface ApiError {
  code: number;
  i18nKey: string;
  message: string;
  field?: string;
  details?: Record<string, unknown>;
  requestId: string;
}

export interface PageMeta {
  page: number;
  pageSize: number;
  total: number;
  hasNext: boolean;
}

export interface ProductSummary {
  id: number;
  name: string;
  coverUrl: string;
  minPrice: number;
  maxPrice: number;
  salesCount: number;
  status: ProductStatus;
}

/** 商品列表查询参数。 */
export interface ProductListQuery extends PageQuery {
  q?: string;
}

/** 后台商品列表查询参数。 */
export interface AdminProductQuery extends ProductListQuery {}

/** 商品 SKU 创建输入。 */
export interface ProductSkuCreateInput {
  code: string;
  name: string;
  priceCents: number;
  costCents?: number;
  physicalStock?: number;
  safetyStock?: number;
  weightGrams?: number | null;
  image?: string;
  barCode?: string;
  status?: 'ACTIVE' | 'DISABLED';
  sortOrder?: number;
  specs?: Record<string, string>;
}

/** 后台商品创建输入。 */
export interface ProductCreateInput {
  categoryId?: number | null;
  name: string;
  subtitle?: string;
  brand?: string;
  mainImages?: Array<Record<string, unknown>>;
  detailImages?: string[];
  detailHtml?: string;
  seoTitle?: string | null;
  seoDescription?: string | null;
  seoKeywords?: string | null;
  specDefinitions?: Array<{
    name: string;
    sortOrder?: number;
    values?: Array<{ value: string; sortOrder?: number }>;
  }>;
  description?: string;
  status?: 'DRAFT' | 'ON_SHELF' | 'OFF_SHELF';
  skus: ProductSkuCreateInput[];
}

/** 后台商品更新输入。 */
export interface ProductUpdateInput {
  name?: string;
  subtitle?: string;
  brand?: string;
  description?: string;
  detailHtml?: string;
  detailImages?: string[];
  status?: 'DRAFT' | 'ON_SHELF' | 'OFF_SHELF';
}

/** 后台发货输入。 */
export interface ShipOrderInput {
  logisticsCompanyCode: string;
  trackingNo: string;
}

/** 后台订单备注和地址快照输入。 */
export interface OrderManagementInput {
  remark?: string;
  addressSnapshot?: Record<string, string>;
}

export interface SkuSnapshot {
  skuId: number;
  skuCode: string;
  name: string;
  priceCents: number;
  quantity: number;
  specs: Record<string, string>;
}

export interface CartItem extends SkuSnapshot {
  id: number;
  stale: boolean;
  staleReason?: 'off_shelf' | 'price_changed' | 'stock_insufficient';
}

export interface OrderSummary {
  id: number;
  orderNo: string;
  status: OrderStatus;
  totalAmount: number;
  productAmount: number;
  freightAmount: number;
  discountAmount: number;
  createdAt: string;
}

/** 支付单创建结果，金额为整数分。 */
export interface PaymentResponse {
  id: number | string;
  orderId: number;
  provider: PaymentProvider;
  status?: string;
  amountCents: number;
}

export interface PaymentRequest {
  orderId: number;
  provider: PaymentProvider;
  requestId: string;
  amountCents: number;
}

/** 短信验证码请求。 */
export interface SmsCodeRequest {
  phone: string;
  purpose?: string;
}
/** 手机号登录请求。 */
export interface LoginRequest {
  phone: string;
  code: string;
}
/** 购物车新增或更新请求。 */
export interface CartItemInput {
  skuId: number;
  quantity: number;
}
/** 订单明细快照。 */
export interface OrderItemInput {
  skuId: number;
  quantity: number;
  priceCents: number;
}
/** 创建订单请求，金额均为整数分。 */
export interface OrderCreateRequest {
  items: OrderItemInput[];
  addressSnapshot: Record<string, string>;
  totalAmount: number;
  productAmount?: number;
  freightAmount?: number;
}
/** 支付创建请求。 */
export interface PaymentCreateRequest {
  orderId: number;
  provider: PaymentProvider;
  amountCents: number;
}
/** 分页查询参数。 */
export interface PageQuery {
  page?: number;
  pageSize?: number;
}
/** 分页响应。 */
export interface PageResponse<T> {
  items: T[];
  meta: PageMeta;
}
/** 商品详情。 */
export interface ProductDetail extends ProductSummary {
  description: string;
  skus: SkuSnapshot[];
}

/** 商品规格定义与详情图数据。 */
export interface ProductSpecDefinition {
  id: number;
  name: string;
  sortOrder: number;
  values: Array<{ id: number; value: string; sortOrder: number }>;
}

export interface ProductDetailResponse extends ProductDetail {
  subtitle: string;
  brand: string;
  detailHtml: string;
  detailImages: string[];
  specDefinitions: ProductSpecDefinition[];
  seoTitle?: string | null;
  seoDescription?: string | null;
  seoKeywords?: string | null;
}

/** 购物车行和收货地址。 */
export interface CartResponse {
  items: CartItem[];
}
export interface Address {
  id: number;
  receiverName: string;
  phone: string;
  provinceCode: string;
  cityCode: string;
  districtCode: string;
  detail: string;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 用户资料响应。 */
export interface UserProfile {
  id: number | string;
  phone: string;
  nickname: string;
  avatar: string;
  gender: string;
  status: string;
  birthday: string | null;
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
}

/** 收货地址写入输入。 */
export interface AddressInput {
  receiverName: string;
  phone: string;
  provinceCode: string;
  cityCode: string;
  districtCode: string;
  detail: string;
  isDefault: boolean;
}

/** 站内通知条目。 */
export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  content: string;
  readAt: string | null;
  createdAt: string;
}

/** 站内通知响应。 */
export interface NotificationResponse {
  items: NotificationItem[];
  unreadCount: number;
}

/** 商品评价条目。 */
export interface ProductReviewItem {
  id: number;
  rating: number;
  content: string;
  images: string[];
  createdAt: string;
}

/** 商品评价响应。 */
export interface ProductReviewResponse {
  averageRating: number;
  items: ProductReviewItem[];
}

/** 管理端登录输入。 */
export interface AdminLoginInput {
  phone: string;
  code: string;
}

/** 管理端登录响应。 */
export interface AdminLoginResult {
  accessToken: string;
  refreshToken?: string;
}

export interface OrderItemResponse {
  id: number;
  skuId: number;
  productId: number;
  productName: string;
  skuCode: string;
  skuName: string;
  specValues: Record<string, string>;
  productImage: string;
  quantity: number;
  priceCents: number;
  weightGrams: number | null;
  discountAmount: number;
  totalAmount: number;
}

export interface OrderDetail extends OrderSummary {
  refundStatus: string;
  paidAmount: number | null;
  paidAt: string | null;
  shippedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  cancelReason: string | null;
  addressSnapshot: Record<string, string>;
  remark: string | null;
  shippingCompanyCode: string;
  trackingNo: string;
  items: OrderItemResponse[];
}

export interface FreightCalculateRequest {
  items: Array<{ skuId: number; quantity: number }>;
  provinceCode: string;
  productAmount: number;
  templateId?: number;
}
export interface FreightCalculateResponse {
  freightAmount: number;
}
export interface RefundResponse {
  id: number;
  refundNo: string;
  paymentId: number;
  amountCents: number;
  status: string;
}

/** 管理后台数据看板与库存行。 */
export interface DashboardData {
 