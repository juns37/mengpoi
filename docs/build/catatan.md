---
sidebar_position: 1
---
import Highlight from '@site/src/components/Highlight';

# Catatan saya

## Highlight
/src/components/Highlight.js
```js
import React from 'react';

export default function Highlight({ children, color, href, variant = 'solid' }) {
  // Pengaturan gaya default
  const baseStyle = {
    borderRadius: '20px',
    padding: '7px 10px',
    cursor: 'pointer',
    textDecoration: 'none',
    display: 'inline-block',
    fontWeight: '500',
    transition: '0.3s',
    margin: '5px'
  };

  // Logika untuk mengubah gaya berdasarkan varian
  const variants = {
    solid: {
      backgroundColor: color,
      color: '#fff',
      border: 'none',
    },
    outline: {
      backgroundColor: 'transparent',
      color: color,
      border: `2px solid ${color}`,
    },
    shadow: {
      backgroundColor: color,
      color: '#fff',
      boxShadow: `0 4px 14px 0 ${color}80`, // 80 untuk transparansi shadow
    }
  };

  const finalStyle = { ...baseStyle, ...variants[variant] };

  return (
    <a href={href} style={finalStyle}>
      {children}
    </a>
  );
}
```

file .md
```
import Highlight from '@site/src/components/Highlight';
```

### Berbagai Gaya Tombol

Gaya Standar
```
<Highlight color="#25c2a0" href="#">Solid Green</Highlight>
```
<Highlight color="#25c2a0" href="#">Solid Green</Highlight>

Gaya Outline (Garis Pinggir)
```
<Highlight color="#1877F2" variant="outline" href="#">Outline Facebook</Highlight>
```
<Highlight color="#1877F2" variant="outline" href="#">Outline Facebook</Highlight>

Gaya Shadow (Bercahaya)
```
<Highlight color="#ff4757" variant="shadow" href="#">Shadow Red</Highlight>
```
<Highlight color="#ff4757" variant="shadow" href="#">Shadow Red</Highlight>