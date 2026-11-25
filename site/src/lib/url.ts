// Prefix an internal path with the site base (e.g. /BeeHive), so links work on GitHub Pages and locally.
export const url = (p: string) => import.meta.env.BASE_URL.replace(/\/$/, "") + p;
