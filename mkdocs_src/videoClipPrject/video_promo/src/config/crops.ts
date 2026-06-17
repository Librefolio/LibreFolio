export type CropRect = {
  x: number; // 0 to 1
  y: number; // 0 to 1
  w: number; // width (0 to 1)
  h: number; // height (0 to 1)
};

export const cropPresets = {
  dashboard: {
    heroCards: { x: 0.05, y: 0.12, w: 0.60, h: 0.25 } as CropRect,
    allocationChart: { x: 0.65, y: 0.12, w: 0.30, h: 0.40 } as CropRect,
    leftSidebar: { x: 0.00, y: 0.00, w: 0.20, h: 1.00 } as CropRect,
  },
  assetChart: {
    toolbar: { x: 0.05, y: 0.05, w: 0.90, h: 0.15 } as CropRect,
    mainChart: { x: 0.05, y: 0.20, w: 0.90, h: 0.45 } as CropRect,
    lowerSignals: { x: 0.05, y: 0.65, w: 0.90, h: 0.30 } as CropRect,
  },
  importWizard: {
    content: { x: 0.15, y: 0.15, w: 0.70, h: 0.60 } as CropRect,
  },
};
