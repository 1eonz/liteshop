import { SiteRenderer } from '../src/components/SiteRenderer';
import { getSitePage } from '../src/site-data';

export default function HomePage(): JSX.Element {
  const page = getSitePage('home');
  if (!page) return <main>页面不存在</main>;
  return <SiteRenderer page={page} />;
}
