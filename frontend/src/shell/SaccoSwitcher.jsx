import { useCallback, useEffect, useRef, useState } from 'react';
import { describe } from '../lib/errors.js';
import { useSession } from '../lib/session.jsx';
import Icon from './Icon.jsx';
import usePopupFocus from './usePopupFocus.js';

function statusStyle(status) {
  const value = String(status || '').toLowerCase();
  if (value === 'suspended') return 'bad';
  if (value === 'active') return 'up';
  return 'warn';
}

export default function SaccoSwitcher({ open, onToggle, onClose, onSelect }) {
  const { sacco, saccoId, saccos, toast } = useSession();
  const enterableSaccos = saccos.filter(item => item.membershipStatus === 'active');
  const [switching, setSwitching] = useState(false);
  const triggerRef = useRef(null);
  const wrapRef = useRef(null);

  const close = useCallback(() => {
    onClose();
    if (triggerRef.current) triggerRef.current.focus();
  }, [onClose]);
  const menuRef = usePopupFocus(open, close);

  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) onClose();
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open, onClose]);

  async function choose(nextSacco) {
    close();
    if (String(nextSacco.id) === String(saccoId)) return;
    setSwitching(true);
    try {
      await onSelect(nextSacco.id);
    } catch (error) {
      toast(describe(error).text, 'err');
    } finally {
      setSwitching(false);
    }
  }

  if (!sacco || !enterableSaccos.length) return null;

  return (
    <div className="switcher-wrap" ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        className="switcher"
        onClick={onToggle}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Circle: ${sacco.name}. Switch circle`}
      >
        <span className="max-w-40 truncate">{sacco.name}</span>
        <Icon name="chevron" className="size-4 shrink-0" />
      </button>
      {open && (
        <div
          ref={menuRef}
          className="switcher-menu glass"
          role="menu"
          aria-label="Choose a SACCO"
          tabIndex="-1"
        >
          {enterableSaccos.map(item => (
            <button
              key={item.id}
              type="button"
              role="menuitemradio"
              aria-checked={String(item.id) === String(saccoId)}
              disabled={switching}
              onClick={() => choose(item)}
            >
              <span>{item.name}</span>
              <span className={`chip ${statusStyle(item.status)}`}>{item.status || 'Active'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
