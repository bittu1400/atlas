import React from 'react';

// The vocabulary a Run is assembled from is not guessable from an ID, and an
// operator who does not know what a Domain carries cannot tell that replacing
// one costs a Research Profile. These captions are the GLOSSARY entries, shown
// where the choice is made.

export const FieldNote: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{children}</p>
);
