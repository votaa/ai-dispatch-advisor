import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  h1: ({ children }) => <h3>{children}</h3>,
  h2: ({ children }) => <h4>{children}</h4>,
  h3: ({ children }) => <h5>{children}</h5>,
  h4: ({ children }) => <h6>{children}</h6>,
  h5: ({ children }) => <h6>{children}</h6>,
  h6: ({ children }) => <h6>{children}</h6>,
  table: ({ children }) => (
    <div className="copilot-table-scroll" role="region" aria-label="Copilot response table" tabIndex={0}>
      <table>{children}</table>
    </div>
  ),
  a: ({ children, href }) => {
    if (!href) return <span>{children}</span>;
    const external = Boolean(href && /^https?:\/\//i.test(href));
    return (
      <a href={href} rel={external ? "noopener noreferrer" : undefined} target={external ? "_blank" : undefined}>
        {children}
      </a>
    );
  },
  img: ({ alt }) => alt ? <span>{alt}</span> : null
};

function safeUrl(url: string) {
  const transformed = defaultUrlTransform(url);
  return /^(https?:|mailto:|\/|#)/i.test(transformed) ? transformed : "";
}

export function CopilotMarkdown({ children }: { children: string }) {
  return (
    <div className="copilot-markdown">
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm]}
        skipHtml
        urlTransform={safeUrl}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
