import { SiteRenderer } from '../src/components/SiteRenderer';
import { loadSitePage } from '../src/site-data.server';

export const revalidate = 60;

export default async function HomePage(): Promise<JSX.Element> {
  const page = await loadSitePage('home');
  if (!page) return <main>页面不存在</main>;
  return <SiteRenderer page={page} />;
}
