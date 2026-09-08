import type {
  AfterSaleStatus,
  AfterSaleType,
  InventoryEventType,
  OrderStatus,
  PaymentProvider,
  ProductStatus,
} from './enums.js';

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
  priceCents: number;
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
  remark?: string;
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
  merchantReply?: string | null;
  merchantRepliedAt?: string | null;
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
  expiresIn?: number;
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
  expiredAt?: string | null;
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

/** 用户提交商品评价输入。 */
export interface ReviewCreateInput {
  orderItemId: number;
  rating: number;
  content: string;
  images?: string[];
}

/** 后台评价审核条目。 */
export interface AdminReviewRecord {
  id: number;
  productId: number;
  skuId: number;
  userId: number;
  rating: number;
  content: string;
  images: string[];
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reason: string | null;
  merchantReply: string | null;
  merchantRepliedAt: string | null;
  createdAt: string;
}

/** 售后单摘要，金额统一为整数分。 */
export interface AfterSaleSummary {
  id: number;
  afterSaleNo: string;
  orderId: number;
  orderItemId: number;
  type: AfterSaleType;
  status: AfterSaleStatus;
  amountCents: number;
  reason: string;
  createdAt: string;
  updatedAt: string;
}

/** 售后申请输入。 */
export interface AfterSaleCreateInput {
  orderItemId: number;
  type: AfterSaleType;
  amountCents: number;
  reason: string;
  evidenceUrls?: string[];
}

/** 售后单完整响应，供 H5 与后台审核页面共用。 */
export interface AfterSaleRecord extends AfterSaleSummary {
  evidenceUrls: string[];
  returnTrackingNo: string;
  auditReason: string | null;
}

/** 管理后台数据看板与库存行。 */
export interface DashboardData {
  metrics: {
    salesAmount: number;
    orderCount: number;
    productCount: number;
    pendingShipmentCount: number;
  };
  trend: Array<{ date: string; amount: number; orderCount?: number }>;
  ranking: Array<{ name: string; salesCount: number }>;
  todo?: { pendingShipments: number; lowStockSkus: number; auditItems: number };
}
export interface InventoryRow {
  skuId: number;
  skuCode: string;
  name: string;
  physicalStock: number;
  availableStock: number;
  lockedStock: number;
  safetyStock: number;
  warning: boolean;
}

export interface CategorySummary {
  id: number;
  parentId: number | null;
  name: string;
  icon: string;
  sortOrder: number;
  isActive?: boolean;
}
export interface AuditLogEntry {
  id: number;
  adminId: number | null;
  resourceType: string;
  resourceId: number | null;
  action: string;
  requestId: string;
  beforeData: Record<string, unknown> | null;
  afterData: Record<string, unknown> | null;
  ip: string;
  userAgent: string;
  createdAt: string;
}
export interface AdminRole {
  id: number;
  name: string;
  permissions: string[];
}
export interface AdminPermission {
  id: number;
  code: string;
}

/** 后台角色分配页面的管理员最小快照。 */
export interface AdminUserRecord {
  id: number;
  nickname: string;
  phone: string;
  roleIds: number[];
}

export type MemberLevel = 'NORMAL' | 'MEMBER';

export interface MemberSummary {
  id: number;
  nickname: string;
  avatar: string;
  phone: string;
  memberLevel: MemberLevel;
  points: number;
  tags: string[];
  createdAt: string;
  orderCount: number;
  totalSpent: number;
}

export interface MemberDetail extends MemberSummary {
  addresses: Array<{
    id: number;
    receiverName: string;
    phone: string;
    detail: string;
    isDefault: boolean;
  }>;
  orders: Array<{
    id: number;
    orderNo: string;
    status: string;
    totalAmount: number;
  }>;
}

export type ContactFormStatus = 'NEW' | 'IN_PROGRESS' | 'RESOLVED' | 'SPAM';

/** 官网联系表单后台摘要。金额和敏感凭证不在此模型中。 */
export interface ContactSubmission {
  id: number;
  name: string;
  email: string;
  phone: string;
  company: string;
  message: string;
  status: ContactFormStatus;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface FreightTemplateItem {
  id: number;
  regionCodes: string[];
  firstUnit: string;
  firstFee: number;
  additionalUnit: string;
  additionalFee: number;
  freeCondition: Record<string, unknown> | null;
}

/** 官网低代码组件类型，与商城组件共同使用版本化页面载体。 */
export type SiteComponentType =
  | 'Navbar'
  | 'Footer'
  | 'Section'
  | 'Divider'
  | 'Hero'
  | 'HeroSplit'
  | 'Hero3D'
  | 'Features'
  | 'Stats'
  | 'LogoWall'
  | 'Testimonials'
  | 'Pricing'
  | 'FAQ'
  | 'ImageWithText'
  | 'ContactForm'
  | 'CTA'
  | 'Hero3DBackground'
  | 'Product3DViewer';

export type StoreComponentType =
  | 'SearchBar'
  | 'Carousel'
  | 'CategoryGrid'
  | 'ProductGrid'
  | 'ActivityBanner'
  | 'Tabbar'
  | 'RichText'
  | 'ImageBanner'
  | 'Spacer'
  | 'ProductList'
  | 'ProductCarousel'
  | 'CouponBlock'
  | 'AnnouncementBar'
  | SiteComponentType;

export interface StoreComponentSchema {
  id: string;
  type: StoreComponentType;
  props: Record<string, unknown>;
  style: Record<string, string>;
  animation?: { enabled: boolean; type: string };
}

export interface StorePageSchema {
  id: number;
  slug: string;
  channel?: 'store' | 'site';
  name?: string;
  title?: string;
  description?: string;
  status?: 'DRAFT' | 'PUBLISHED';
  publishedAt?: string | null;
  seo?: Record<string, unknown>;
  pageStyle?: Record<string, string>;
  animation?: Record<string, unknown>;
  version: number;
  isHome: boolean;
  components: StoreComponentSchema[];
}
export interface FreightTemplate {
  id: number;
  name: string;
  type: 'WEIGHT' | 'PIECE' | 'REGION';
  isDefault: boolean;
  enabled: boolean;
  items: FreightTemplateItem[];
  createdAt: string;
  updatedAt: string;
}

export interface InventoryLedgerEntry {
  id: number;
  skuId: number;
  eventType: InventoryEventType;
  quantity: number;
  availableAfter: number;
  lockedAfter: number;
  referenceNo?: string;
  reason?: string | null;
  physicalBefore?: number;
  physicalAfter?: number;
  lockedBefore?: number;
  createdAt: string;
}
