export interface ProductFormState {
  name: string;
  subtitle: string;
  brand: string;
  description: string;
  status: 'DRAFT' | 'ON_SHELF' | 'OFF_SHELF';
  skuCode: string;
  skuName: string;
  priceCents: string;
  physicalStock: string;
}

export const INITIAL_PRODUCT_FORM: ProductFormState = {
  name: '',
  subtitle: '',
  brand: '',
  description: '',
  status: 'DRAFT',
  skuCode: 'NEW-SKU-001',
  skuName: '标准款',
  priceCents: '12900',
  physicalStock: '100',
};
