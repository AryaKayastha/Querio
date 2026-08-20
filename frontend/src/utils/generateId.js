export const generateId = (prefix = "id") => {
  const randomPart = Math.random().toString(36).slice(2, 9);
  const timePart = Date.now().toString(36);
  return `${prefix}-${timePart}-${randomPart}`;
};
