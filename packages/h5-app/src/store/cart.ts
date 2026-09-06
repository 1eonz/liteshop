import { create } from 'zustand';

export interface CartLine {
  skuId: number;
  quantity: number;
  priceCents: number;
}

interface CartState {
  lines: CartLine[];
  addLine: (line: CartLine) => void;
  setLines: (lines: CartLine[]) => void;
  updateLine: (skuId: number, quantity: number) => void;
  removeLine: (skuId: number) => void;
  clear: () => void;
}

/** 购物车客户端状态，服务端数据不存放在 Zustand。 */
export const useCartStore = create<CartState>((set) => ({
  lines: [],
  addLine: (line) =>
    set((state) => {
      const existing = state.lines.find((item) => item.skuId === line.skuId);
      if (existing)
        return {
          lines: state.lines.map((item) =>
            item.skuId === line.skuId ? { ...item, quantity: item.quantity + line.quantity } : item,
          ),
        };
      return { lines: [...state.lines, line] };
    }),
  setLines: (lines) => set({ lines }),
  updateLine: (skuId, quantity) =>
    set((state) => ({
      lines: state.lines.map((item) => (item.skuId === skuId ? { ...item, quantity } : item)),
    })),
  removeLine: (skuId) =>
    set((state) => ({
      lines: state.lines.filter((item) => item.skuId !== skuId),
    })),
  clear: () => set({ lines: [] }),
}));
