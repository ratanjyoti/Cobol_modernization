import React from 'react';

type Props = {
  title: string;
  description?: string;
};

export default function PageContainer({
  title,
  description
}: Props) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-[var(--text-main)]">
        {title}
      </h1>

      {description && (
        <p className="text-[var(--text-muted)] mt-2 text-lg">
          {description}
        </p>
      )}
    </div>
  );
}
