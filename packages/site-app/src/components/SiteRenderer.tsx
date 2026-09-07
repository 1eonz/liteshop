'use client';

import type { CSSProperties, FormEvent, JSX } from 'react';
import { useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useDebounceAction } from '@liteshop/shared-components';

import type { SiteAnimationConfig, SiteComponentSchema, SitePageSchema } from '../site-data';

interface LinkItem {
  label: string;
  href: string;
  external?: boolean;
}

interface ActionLink {
  label: string;
  href: string;
}

const Hero3DBackground = dynamic(
  () => import('./ThreeSceneFallback').then((module) => module.Hero3DBackground),
  { ssr: false, loading: () => <div className="site-3d-placeholder" aria-label="3D 加载中" /> },
);
const Product3DViewer = dynamic(
  () => import('./ThreeSceneFallback').then((module) => module.Product3DViewer),
  {
    ssr: false,
    loading: () => <div className="site-3d-placeholder" aria-label="产品预览加载中" />,
  },
);

const asRecord = (value: unknown): Record<string, unknown> =>
  typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};

const stringProp = (props: Record<string, unknown>, key: string, fallback = ''): string => {
  const value = props[key];
  return typeof value === 'string' ? value : fallback;
};

function safeHref(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const href = value.trim();
  if (!href || /^(javascript|data|vbscript):/i.test(href)) return null;
  if (
    href.startsWith('/') ||
    href.startsWith('#') ||
    href.startsWith('mailto:') ||
    href.startsWith('tel:')
  ) {
    return href;
  }
  try {
    const parsed = new URL(href);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? href : null;
  } catch {
    return null;
  }
}

const actionProp = (value: unknown): ActionLink | null => {
  const action = asRecord(value);
  const label = typeof action.label === 'string' ? action.label : '';
  const href = safeHref(action.href);
  return label && href ? { label, href } : null;
};

const linksProp = (value: unknown): LinkItem[] => {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item): LinkItem[] => {
    const link = asRecord(item);
    const label = typeof link.label === 'string' ? link.label : '';
    const href = safeHref(link.href);
    return label && href ? [{ label, href, external: link.external === true }] : [];
  });
};

const animationClass = (animation?: SiteAnimationConfig): string => {
  if (!animation?.enabled || animation.type === 'none') return '';
  return `site-reveal site-reveal--${animation.type}`;
};

function ActionButton({
  action,
  secondary = false,
}: {
  action: ActionLink | null;
  secondary?: boolean;
}): JSX.Element | null {
  if (!action) return null;
  return (
    <a
      className={secondary ? 'site-button site-button--secondary' : 'site-button'}
      href={action.href}
    >
      {action.label}
      <span aria-hidden="true">↗</span>
    </a>
  );
}

function Navbar({ props }: { props: Record<string, unknown> }): JSX.Element {
  const [open, setOpen] = useState(false);
  const links = linksProp(props.links);
  const cta = actionProp(props.cta);
  const brandName = stringProp(props, 'brandName', 'LiteShop');
  const logoUrl = stringProp(props, 'logoUrl');
  return (
    <header className="site-navbar">
      <div className="site-container site-navbar__inner">
        <a className="site-brand" href="/" aria-label={`${brandName} 首页`}>
          {logoUrl ? (
            <img className="site-brand__logo" src={logoUrl} alt="" />
          ) : (
            <span className="site-brand__mark" aria-hidden="true">
              L
            </span>
          )}
          <span>{brandName}</span>
        </a>
        <button
          className="site-menu-toggle"
          type="button"
          aria-expanded={open}
          aria-controls="site-navigation"
          onClick={() => setOpen((current) => !current)}
        >
          <span className="sr-only">打开导航</span>
          <span aria-hidden="true">{open ? '×' : '☰'}</span>
        </button>
        <nav
          id="site-navigation"
          className={open ? 'site-navigation site-navigation--open' : 'site-navigation'}
          aria-label="主导航"
        >
          <div className="site-navigation__links">
            {links.map((link) => (
              <a key={`${link.href}-${link.label}`} href={link.href} onClick={() => setOpen(false)}>
                {link.label}
              </a>
            ))}
          </div>
          <ActionButton action={cta} />
        </nav>
      </div>
    </header>
  );
}

function Hero({
  props,
  split = false,
}: {
  props: Record<string, unknown>;
  split?: boolean;
}): JSX.Element {
  const action = actionProp(props.action);
  const primaryAction = actionProp(props.primaryAction) ?? action;
  const secondaryAction = actionProp(props.secondaryAction);
  const imageUrl = stringProp(props, 'image');
  return (
    <section className={split ? 'site-hero site-hero--split' : 'site-hero'}>
      <div className="site-container site-hero__grid">
        <div className="site-hero__copy">
          <p className="site-eyebrow">{stringProp(props, 'eyebrow', 'LITESHOP')}</p>
          <h1>{stringProp(props, 'title')}</h1>
          <p className="site-lede">{stringProp(props, 'description')}</p>
          <div className="site-actions">
            <ActionButton action={primaryAction} />
            <ActionButton action={secondaryAction} secondary />
          </div>
        </div>
        {imageUrl ? (
          <figure className="site-hero__media">
            <img src={imageUrl} alt={stringProp(props, 'imageAlt', 'LiteShop 工作场景')} />
            <figcaption>{stringProp(props, 'caption')}</figcaption>
          </figure>
        ) : (
          <div className="site-hero__signal" aria-hidden="true">
            <span className="site-signal-card site-signal-card--top">
              可用库存 <strong>1,286</strong>
            </span>
            <span className="site-signal-card site-signal-card--middle">
              今日订单 <strong>248</strong>
            </span>
            <span className="site-signal-card site-signal-card--bottom">
              履约率 <strong>99.95%</strong>
            </span>
          </div>
        )}
      </div>
    </section>
  );
}

function Features({ props }: { props: Record<string, unknown> }): JSX.Element {
  const items = Array.isArray(props.items) ? props.items : [];
  return (
    <section className="site-section">
      <div className="site-container">
        <div className="site-section__heading">
          <p className="site-eyebrow">{stringProp(props, 'eyebrow')}</p>
          <h2>{stringProp(props, 'title', '核心能力')}</h2>
        </div>
        <div className="site-feature-grid">
          {items.map((value, index) => {
            const item = asRecord(value);
            return (
              <article
                className="site-feature"
                key={`${stringProp(item, 'title', 'feature')}-${index}`}
              >
                <span className="site-feature__icon" aria-hidden="true">
                  {stringProp(item, 'icon', `0${index + 1}`)}
                </span>
                <h3>{stringProp(item, 'title')}</h3>
                <p>{stringProp(item, 'description')}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Stats({ props }: { props: Record<string, unknown> }): JSX.Element {
  const items = Array.isArray(props.items) ? props.items : [];
  return (
    <section className="site-stats" aria-label="LiteShop 数据">
      <div className="site-container site-stats__grid">
        {items.map((value, index) => {
          const item = asRecord(value);
          return (
            <div className="site-stat" key={`${stringProp(item, 'label', 'stat')}-${index}`}>
              <strong>{stringProp(item, 'value')}</strong>
              <span>{stringProp(item, 'label')}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function LogoWall({ props }: { props: Record<string, unknown> }): JSX.Element {
  const items = Array.isArray(props.items) ? props.items : [];
  return (
    <section className="site-section site-section--compact">
      <div className="site-container">
        <p className="site-section__label">{stringProp(props, 'title')}</p>
        <div className="site-logo-wall">
          {items.map((item, index) => (
            <span key={`${String(item)}-${index}`}>{String(item)}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Testimonials({ props }: { props: Record<string, unknown> }): JSX.Element {
  const items = Array.isArray(props.items) ? props.items : [];
  return (
    <section className="site-section site-section--tint">
      <div className="site-container">
        <div className="site-section__heading">
          <p className="site-eyebrow">真实反馈</p>
          <h2>把时间用在更重要的事情上</h2>
        </div>
        <div className="site-testimonial-grid">
          {items.map((value, index) => {
            const item = asRecord(value);
            return (
              <figure
                className="site-testimonial"
                key={`${stringProp(item, 'name', 'quote')}-${index}`}
              >
                <blockquote>“{stringProp(item, 'quote')}”</blockquote>
                <figcaption>
                  <strong>{stringProp(item, 'name')}</strong>
                  <span>{stringProp(item, 'role')}</span>
                </figcaption>
              </figure>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Pricing({ props }: { props: Record<string, unknown> }): JSX.Element {
  const plans = Array.isArray(props.plans) ? props.plans : [];
  return (
    <section className="site-section">
      <div className="site-container">
        <div className="site-section__heading">
          <p className="site-eyebrow">{stringProp(props, 'eyebrow')}</p>
          <h2>{stringProp(props, 'title', '选择适合你的节奏')}</h2>
        </div>
        <div className="site-pricing-grid">
          {plans.map((value, index) => {
            const plan = asRecord(value);
            const features = Array.isArray(plan.features) ? plan.features : [];
            return (
              <article
                className={
                  plan.recommended === true
                    ? 'site-price-card site-price-card--featured'
                    : 'site-price-card'
                }
                key={`${stringProp(plan, 'name', 'plan')}-${index}`}
              >
                {plan.recommended === true && (
                  <span className="site-price-card__badge">最受欢迎</span>
                )}
                <h3>{stringProp(plan, 'name')}</h3>
                <p className="site-price-card__description">{stringProp(plan, 'description')}</p>
                <p className="site-price-card__price">
                  <strong>{stringProp(plan, 'price')}</strong>
                  <span>{stringProp(plan, 'period')}</span>
                </p>
                <ul>
                  {features.map((feature) => (
                    <li key={String(feature)}>
                      <span aria-hidden="true">✓</span>
                      {String(feature)}
                    </li>
                  ))}
                </ul>
                <ActionButton
                  action={actionProp(plan.action)}
                  secondary={plan.recommended !== true}
                />
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FAQ({ props }: { props: Record<string, unknown> }): JSX.Element {
  const items = Array.isArray(props.items) ? props.items : [];
  return (
    <section id={stringProp(props, 'id', 'faq')} className="site-section site-section--narrow">
      <div className="site-container site-container--reading">
        <div className="site-section__heading">
          <h2>{stringProp(props, 'title', '常见问题')}</h2>
        </div>
        <div className="site-faq">
          {items.map((value, index) => {
            const item = asRecord(value);
            return (
              <details key={`${stringProp(item, 'question', 'faq')}-${index}`} open={index === 0}>
                <summary>{stringProp(item, 'question')}</summary>
                <p>{stringProp(item, 'answer')}</p>
              </details>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ImageWithText({ props }: { props: Record<string, unknown> }): JSX.Element {
  const action = actionProp(props.action);
  return (
    <section id={stringProp(props, 'id')} className="site-section site-image-text">
      <div className="site-container site-image-text__grid">
        <img
          src={stringProp(props, 'image')}
          alt={stringProp(props, 'imageAlt', 'LiteShop 团队协作')}
        />
        <div>
          <p className="site-eyebrow">{stringProp(props, 'eyebrow')}</p>
          <h2>{stringProp(props, 'title')}</h2>
          <p className="site-lede">{stringProp(props, 'description')}</p>
          <ActionButton action={action} secondary />
        </div>
      </div>
    </section>
  );
}

function ContactForm({ props }: { props: Record<string, unknown> }): JSX.Element {
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const formRef = useRef<HTMLFormElement>(null);
  const submitPayload = async (payload: {
    name: string;
    email: string;
    phone: string;
    company: string;
    message: string;
    website: string;
  }): Promise<void> => {
    setStatus('submitting');
    setMessage('');
    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-request-id': crypto.randomUUID() },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('contact_failed');
      formRef.current?.reset();
      setStatus('success');
      setMessage('已收到，我们会在一个工作日内回复。');
    } catch {
      setStatus('error');
      setMessage('提交未完成，请稍后重试或直接发送邮件。');
    }
  };
  const [runSubmit, submitting] = useDebounceAction(submitPayload, 1000);
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      name: String(form.get('name') ?? ''),
      email: String(form.get('email') ?? ''),
      phone: String(form.get('phone') ?? ''),
      company: String(form.get('company') ?? ''),
      message: String(form.get('message') ?? ''),
      website: String(form.get('website') ?? ''),
    };
    void runSubmit(payload);
  };
  return (
    <section className="site-section site-section--tint">
      <div className="site-container site-container--reading">
        <div className="site-section__heading">
          <p className="site-eyebrow">联系团队</p>
          <h2>{stringProp(props, 'title', '预约一次对话')}</h2>
          <p>{stringProp(props, 'description')}</p>
        </div>
        <form ref={formRef} className="site-contact-form" onSubmit={submit}>
          <div className="site-form-grid">
            <label>
              姓名
              <input name="name" required autoComplete="name" />
            </label>
            <label>
              工作邮箱
              <input name="email" required type="email" autoComplete="email" />
            </label>
            <label>
              联系电话
              <input name="phone" type="tel" autoComplete="tel" />
            </label>
            <label>
              公司名称
              <input name="company" autoComplete="organization" />
            </label>
          </div>
          <label>
            你正在解决什么问题？
            <textarea name="message" required rows={5} />
          </label>
          <label className="site-honeypot" aria-hidden="true">
            网站
            <input name="website" tabIndex={-1} autoComplete="off" />
          </label>
          <button
            className="site-button"
            type="submit"
            disabled={submitting || status === 'submitting'}
          >
            {submitting || status === 'submitting' ? '提交中…' : '提交信息'}
            <span aria-hidden="true">↗</span>
          </button>
          <p className="site-form-status" aria-live="polite" data-status={status}>
            {message}
          </p>
        </form>
      </div>
    </section>
  );
}

function Footer({ props }: { props: Record<string, unknown> }): JSX.Element {
  const groups = Array.isArray(props.groups) ? props.groups : [];
  return (
    <footer className="site-footer">
      <div className="site-container">
        <div className="site-footer__grid">
          <div>
            <a className="site-brand site-brand--footer" href="/">
              <span className="site-brand__mark" aria-hidden="true">
                L
              </span>
              <span>LiteShop</span>
            </a>
            <p>轻盈经营每一笔订单。</p>
          </div>
          {groups.map((value, index) => {
            const group = asRecord(value);
            const links = linksProp(group.links);
            return (
              <div key={`${stringProp(group, 'title', 'group')}-${index}`}>
                <h3>{stringProp(group, 'title')}</h3>
                {links.map((link) => (
                  <a key={`${link.href}-${link.label}`} href={link.href}>
                    {link.label}
                  </a>
                ))}
              </div>
            );
          })}
        </div>
        <p className="site-footer__copyright">{stringProp(props, 'copyright')}</p>
      </div>
    </footer>
  );
}

function Section({
  props,
  children,
}: {
  props: Record<string, unknown>;
  children: JSX.Element;
}): JSX.Element {
  const style = props.style;
  const inlineStyle: CSSProperties =
    typeof style === 'object' && style !== null ? (style as CSSProperties) : {};
  return (
    <section
      id={stringProp(props, 'id')}
      className="site-section site-section--custom"
      style={inlineStyle}
    >
      <div className="site-container">
        <p className="site-eyebrow">{stringProp(props, 'eyebrow')}</p>
        <h2>{stringProp(props, 'title')}</h2>
        <p className="site-lede">{stringProp(props, 'body')}</p>
        {children}
      </div>
    </section>
  );
}

function renderComponent(component: SiteComponentSchema): JSX.Element {
  const key = component.id;
  const props = component.props;
  switch (component.type) {
    case 'Navbar':
      return <Navbar key={key} props={props} />;
    case 'Footer':
      return <Footer key={key} props={props} />;
    case 'Hero':
      return (
        <div key={key} className={animationClass(component.animation)}>
          <Hero props={props} />
        </div>
      );
    case 'HeroSplit':
      return (
        <div key={key} className={animationClass(component.animation)}>
          <Hero props={props} split />
        </div>
      );
    case 'Hero3D':
    case 'Hero3DBackground':
      return (
        <Hero3DBackground
          key={key}
          title={stringProp(props, 'title')}
          description={stringProp(props, 'description')}
          fallbackUrl={stringProp(props, 'fallbackUrl')}
        />
      );
    case 'Features':
      return (
        <div key={key} className={animationClass(component.animation)}>
          <Features props={props} />
        </div>
      );
    case 'Stats':
      return <Stats key={key} props={props} />;
    case 'LogoWall':
      return <LogoWall key={key} props={props} />;
    case 'Testimonials':
      return <Testimonials key={key} props={props} />;
    case 'Pricing':
      return <Pricing key={key} props={props} />;
    case 'FAQ':
      return <FAQ key={key} props={props} />;
    case 'ImageWithText':
      return <ImageWithText key={key} props={props} />;
    case 'ContactForm':
      return <ContactForm key={key} props={props} />;
    case 'CTA':
      return (
        <section key={key} className="site-cta">
          <div className="site-container site-cta__inner">
            <div>
              <p className="site-eyebrow">LITESHOP</p>
              <h2>{stringProp(props, 'title')}</h2>
              <p>{stringProp(props, 'description')}</p>
            </div>
            <ActionButton action={actionProp(props.action)} />
          </div>
        </section>
      );
    case 'Divider':
      return <hr key={key} className="site-divider" />;
    case 'Section':
      return (
        <Section key={key} props={props}>
          <span />
        </Section>
      );
    case 'Product3DViewer':
      return (
        <Product3DViewer
          key={key}
          title={stringProp(props, 'title', '产品空间预览')}
          description={stringProp(props, 'description', '当前设备使用轻量化预览。')}
          fallbackUrl={stringProp(props, 'fallbackUrl')}
        />
      );
    default:
      return <div key={key} />;
  }
}

export function SiteRenderer({ page }: { page: SitePageSchema }): JSX.Element {
  const pageStyle = page.pageStyle ?? {};
  return (
    <div className="site-shell" style={pageStyle}>
      {page.components.map(renderComponent)}
    </div>
  );
}
