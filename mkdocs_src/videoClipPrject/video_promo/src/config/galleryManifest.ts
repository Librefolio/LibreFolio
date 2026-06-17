export const promoGallery = {
  dashboard: {
    main: "dashboard/main.png",
    allocation: "dashboard/allocation-charts.png",
  },
  transactions: {
    list: "transactions/list.png",
    fxConversion: "transactions/form-modal.png",
    picker: "transactions/picker-modal.png",
  },
  brokers: {
    list: "brokers/list.png",
  },
  assets: {
    list: "assets/list.png",
    chart: "assets/detail-chart.png",
    signals: "assets/detail-signals.png",
    measures: "assets/detail-measures.png",
    classification: "assets/detail-classification.png",
    editor: "assets/detail-editor.png"
  },
  fx: {
    list: "fx/list.png",
    chart: "fx/detail-chart.png",
    signals: "fx/detail-signals.png",
    measures: "fx/detail-measures.png",
  },
  settings: {
    schedulerConfig: "settings/scheduler-config.png",
    schedulerLog: "settings/scheduler-log.png",
  },
  files: {
    csvPreview: "files/preview-modal.png",
  },
} as const;

export const promoGalleryMobile = {
  dashboard: {
    main: "dashboard/main.png",
  },
  assets: {
    list: "assets/list.png",
    chart: "assets/detail-chart.png",
  }
} as const;
