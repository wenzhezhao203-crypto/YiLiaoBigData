export const number = (value: number | null | undefined) => new Intl.NumberFormat("zh-CN").format(value ?? 0);
export const percent = (value: number | null | undefined) => value === null || value === undefined ? "--" : `${(value * 100).toFixed(2)}%`;
export const days = (value: number | null | undefined) => value === null || value === undefined ? "--" : `${value.toFixed(2)} 天`;
export const money = (value: number | null | undefined) => {
  if (value === null || value === undefined) return "--";
  if (Math.abs(value) >= 100000000) return `${(value / 100000000).toFixed(2)} 亿`;
  if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(2)} 万`;
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
};
