import type { MetadataRoute } from 'next';

import { sitePages } from '../src/site-data';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';
  return Object.keys(sitePages).map((slug) => ({
    url: slug === 'home' ? baseUrl : `${baseUrl}/${slug}`,
    lastModified: new Date(),
    changeFrequency: slug === 'home' ? 'daily' : 'monthly',
    priority: slug === 'home' ? 1 : 0.7,
  }));
}
