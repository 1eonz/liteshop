import { NextResponse } from 'next/server';

interface ContactPayload {
  name?: unknown;
  email?: unknown;
  phone?: unknown;
  company?: unknown;
  message?: unknown;
  website?: unknown;
}

const text = (value: unknown): string => (typeof value === 'string' ? value.trim() : '');

export async function POST(request: Request): Promise<NextResponse> {
  let payload: ContactPayload;
  try {
    payload = (await request.json()) as ContactPayload;
  } catch {
    return NextResponse.json({ message: '请求格式不正确' }, { status: 400 });
  }
  const name = text(payload.name);
  const email = text(payload.email);
  const message = text(payload.message);
  if (!name || !email || !message || !email.includes('@')) {
    return NextResponse.json({ message: '请完整填写姓名、邮箱和留言' }, { status: 422 });
  }
  if (text(payload.website)) {
    return NextResponse.json({ accepted: true }, { status: 202 });
  }

  const apiBase =
    process.env.SITE_API_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1';
  const requestId = request.headers.get('x-request-id') ?? crypto.randomUUID();
  try {
    const response = await fetch(`${apiBase.replace(/\/$/, '')}/contact/forms`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-request-id': requestId },
      body: JSON.stringify({
        name,
        email,
        phone: text(payload.phone),
        company: text(payload.company),
        message,
        website: '',
      }),
      cache: 'no-store',
    });
    const responseBody = (await response.json()) as Record<string, unknown>;
    return NextResponse.json(responseBody, { status: response.status });
  } catch {
    return NextResponse.json({ message: '联系服务暂不可用，请稍后重试' }, { status: 503 });
  }
}
