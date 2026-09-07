import { revalidatePath, revalidateTag } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

interface RevalidatePayload {
  slug?: unknown;
  tags?: unknown;
}

function isRecord(value: unknown): value is RevalidatePayload {
  return typeof value === 'object' && value !== null;
}

function isSafeSlug(value: unknown): value is string {
  return typeof value === 'string' && /^[a-z0-9-]+$/.test(value);
}

const ALLOWED_TAGS = new Set([
  'site-pages',
  'site-settings',
  'site-navigation:header',
  'site-navigation:footer',
]);

/** 后台页面发布后的精确 ISR 失效入口。 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const expectedToken = process.env.REVALIDATE_TOKEN ?? '';
  const providedToken = request.headers.get('x-revalidate-token') ?? '';
  if (!expectedToken || providedToken !== expectedToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
  const slug = isRecord(payload) ? payload.slug : undefined;
  if (!isSafeSlug(slug)) {
    return NextResponse.json({ error: 'Invalid slug' }, { status: 422 });
  }

  const tags =
    isRecord(payload) && Array.isArray(payload.tags)
      ? payload.tags.filter(
          (tag): tag is string => typeof tag === 'string' && ALLOWED_TAGS.has(tag),
        )
      : [];
  for (const tag of tags) revalidateTag(tag);
  revalidateTag(`site-page:${slug}`);
  revalidatePath(slug === 'home' ? '/' : `/${slug}`);
  return NextResponse.json({ revalidated: true, slug, now: Date.now() });
}
