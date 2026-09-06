/** API 与各端共享的订单生命周期状态。 */
export enum OrderStatus {
  PENDING_PAYMENT = 'PENDING_PAYMENT',
  PAID = 'PAID',
  SHIPPED = 'SHIPPED',
  COMPLETED = 'COMPLETED',
  CANCELLED = 'CANCELLED',
}

/** 支付渠道标识。 */
export enum PaymentProvider {
  WECHAT = 'WECHAT',
  ALIPAY = 'ALIPAY',
}

/** 库存流水事件类型。 */
export enum InventoryEventType {
  LOCK = 'LOCK',
  DEDUCT = 'DEDUCT',
  RELEASE = 'RELEASE',
  PURCHASE_IN = 'PURCHASE_IN',
  MANUAL_ADJUST = 'MANUAL_ADJUST',
}

/** 商品发布状态。 */
export enum ProductStatus {
  DRAFT = 'DRAFT',
  ON_SHELF = 'ON_SHELF',
  OFF_SHELF = 'OFF_SHELF',
}

/** 商城用户账号状态。 */
export enum UserStatus {
  ACTIVE = 'ACTIVE',
  DISABLED = 'DISABLED',
}

/** 支付单状态，独立于订单正向状态机。 */
export enum PaymentStatus {
  PENDING = 'PENDING',
  SUCCESS = 'SUCCESS',
  FAILED = 'FAILED',
  REFUNDED = 'REFUNDED',
}

/** 一期预置物流公司代码。 */
export enum LogisticsCompanyCode {
  SF = 'SF',
  YTO = 'YTO',
  ZTO = 'ZTO',
  STO = 'STO',
  YD = 'YD',
  JT = 'JT',
  EMS = 'EMS',
  DBL = 'DBL',
  JD = 'JD',
  FAST = 'FAST',
  OTHER = 'OTHER',
}
