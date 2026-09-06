/** 三期 3D 场景预设与设备能力判断，渲染层可映射到 R3F 或轻量降级实现。 */

export const SHARED_3D_COMPONENTS_VERSION = 2 as const;

export type ScenePreset = 'floating-geometry' | 'particle-network' | 'wave-plane' | 'rotating-ring';

export interface Hero3DConfig {
  preset: ScenePreset;
  primaryColor: string;
  secondaryColor: string;
  particleCount: number;
  speed: number;
  opacity: number;
  interactive: boolean;
  mobileFallbackUrl?: string;
}

export interface DeviceCapabilities {
  isMobile: boolean;
  hardwareConcurrency: number;
  deviceMemoryGb: number | null;
  reducedMotion: boolean;
}

/** 返回符合性能预算的默认 3D 配置。颜色必须传入 CSS Token，而不是硬编码色值。 */
export function createHero3DConfig(overrides: Partial<Hero3DConfig> = {}): Hero3DConfig {
  return {
    preset: 'floating-geometry',
    primaryColor: 'var(--color-primary)',
    secondaryColor: 'var(--color-info)',
    particleCount: 36,
    speed: 0.35,
    opacity: 0.72,
    interactive: true,
    ...overrides,
  };
}

/** 根据设备能力和用户偏好决定是否使用移动端降级资源。 */
export function shouldUse3DFallback(capabilities: DeviceCapabilities): boolean {
  if (capabilities.reducedMotion || capabilities.isMobile) return true;
  if (capabilities.hardwareConcurrency > 0 && capabilities.hardwareConcurrency < 4) return true;
  return capabilities.deviceMemoryGb !== null && capabilities.deviceMemoryGb < 4;
}

/** 将动画速度限制在稳定范围，避免配置面板输入极端值造成主线程压力。 */
export function clampSceneSpeed(speed: number): number {
  if (!Number.isFinite(speed)) return 0.35;
  return Math.min(Math.max(speed, 0), 1.5);
}
