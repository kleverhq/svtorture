import { fromMarkdown } from "mdast-util-from-markdown";
import { toString } from "mdast-util-to-string";
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";

import aboutMarkdown from "../../docs/about/README.md?raw";

const REPOSITORY_DOCS =
  "https://github.com/kleverhq/svtorture/tree/main/docs";
const REPOSITORY_BLOB = "https://github.com/kleverhq/svtorture/blob/main";
const ABOUT_SOURCE_PATH = "/docs/about/README.md";

const ABOUT_ASSETS = import.meta.glob<string>(
  "../../docs/about/assets/*",
  { eager: true, import: "default", query: "?url" },
);

const IMAGE_DIMENSIONS: Record<string, readonly [number, number]> = {
  "assets/campaign-to-dashboard.drawio.png": [1280, 646],
  "assets/executable-cases.drawio.png": [1200, 601],
  "assets/standards-to-evidence.drawio.png": [1261, 561],
  "assets/tool-applicability.drawio.png": [1221, 666],
  "assets/traceable-requirements.drawio.png": [1200, 611],
};

type AboutSection = {
  id: string;
  title: string;
  markdown: string;
};

function sectionId(title: string): string {
  return title
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-|-$/g, "");
}

export function sectionsFromMarkdown(markdown: string): AboutSection[] {
  const root = fromMarkdown(markdown);
  const headings = root.children.filter(
    (node) => node.type === "heading" && node.depth === 2,
  );
  const usedIds = new Map<string, number>();

  return headings.map((heading, index) => {
    const title = toString(heading);
    const baseId = sectionId(title) || "section";
    const occurrence = (usedIds.get(baseId) ?? 0) + 1;
    usedIds.set(baseId, occurrence);

    const start = heading.position?.end.offset;
    const end = headings[index + 1]?.position?.start.offset ?? markdown.length;
    if (start === undefined || end === undefined) {
      throw new Error(`missing source position for About section: ${title}`);
    }

    return {
      id: occurrence === 1 ? baseId : `${baseId}-${occurrence}`,
      title,
      markdown: markdown.slice(start, end).trim(),
    };
  });
}

function resolveImage(src: string | undefined): {
  src: string | undefined;
  width: number | undefined;
  height: number | undefined;
} {
  if (!src || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(src)) {
    return { src, width: undefined, height: undefined };
  }

  const normalized = src.replace(/^\.\//, "");
  const resolved = ABOUT_ASSETS[`../../docs/about/${normalized}`];
  if (!resolved) throw new Error(`unknown About image: ${src}`);
  const dimensions = IMAGE_DIMENSIONS[normalized];
  return {
    src: resolved,
    width: dimensions?.[0],
    height: dimensions?.[1],
  };
}

export function resolveLink(href: string | undefined): string | undefined {
  if (!href || href.startsWith("#") || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(href)) {
    return href;
  }

  const resolved = new URL(href, `https://example.invalid${ABOUT_SOURCE_PATH}`);
  return `${REPOSITORY_BLOB}${resolved.pathname}${resolved.search}${resolved.hash}`;
}

function isImageParagraph(node: unknown): boolean {
  if (!node || typeof node !== "object" || !("children" in node)) return false;
  const children = (node as { children?: unknown[] }).children;
  if (children?.length !== 1) return false;
  const child = children[0];
  return Boolean(
    child &&
      typeof child === "object" &&
      "tagName" in child &&
      child.tagName === "img",
  );
}

function MarkdownImage({
  src,
  alt,
  title,
}: {
  src?: string | undefined;
  alt?: string | undefined;
  title?: string | undefined;
}) {
  const label = alt || "About diagram";
  const descriptionId = title
    ? `about-${src?.replace(/[^a-z0-9]+/gi, "-")}-description`
    : undefined;
  const image = resolveImage(src);
  return (
    <figure className="about-figure">
      <div
        className="about-figure__viewport"
        role="region"
        aria-label={`Scrollable diagram: ${label}`}
        tabIndex={0}
      >
        <img
          src={image.src}
          alt={alt || ""}
          width={image.width}
          height={image.height}
          aria-describedby={descriptionId}
          loading="lazy"
          decoding="async"
        />
      </div>
      {title && (
        <span id={descriptionId} className="visually-hidden">
          {title}
        </span>
      )}
    </figure>
  );
}

function MarkdownParagraph({
  node,
  children,
}: {
  node?: unknown;
  children?: ReactNode;
}) {
  return isImageParagraph(node) ? <>{children}</> : <p>{children}</p>;
}

const SECTIONS = sectionsFromMarkdown(aboutMarkdown);

export function AboutView() {
  return (
    <div className="about-view">
      <nav className="about-toc" aria-label="About contents">
        <span className="section-label">On this page</span>
        <ol>
          {SECTIONS.map(({ id, title }, index) => (
            <li key={id}>
              <a href={`#${id}`}>
                <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                {title}
              </a>
            </li>
          ))}
        </ol>
        <a
          className="about-toc__docs"
          href={REPOSITORY_DOCS}
          target="_blank"
          rel="noreferrer"
        >
          Maintainer docs ↗
        </a>
      </nav>

      <article className="about-story" aria-label="About SVTORTURE">
        {SECTIONS.map(({ id, title, markdown }, index) => (
          <section
            className={`about-section${index === SECTIONS.length - 1 ? " about-section--last" : ""}`}
            id={id}
            key={id}
          >
            <div className="about-section__copy">
              <span className="about-section__number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="about-section__markdown">
                <h2>{title}</h2>
                <ReactMarkdown
                  components={{
                    a: ({ href, children }) => {
                      const resolved = resolveLink(href);
                      const external = resolved && !resolved.startsWith("#");
                      return (
                        <a
                          href={resolved}
                          {...(external
                            ? { target: "_blank", rel: "noreferrer" }
                            : {})}
                        >
                          {children}
                        </a>
                      );
                    },
                    img: MarkdownImage,
                    p: MarkdownParagraph,
                  }}
                >
                  {markdown}
                </ReactMarkdown>
              </div>
            </div>
          </section>
        ))}
      </article>
    </div>
  );
}
