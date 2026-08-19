import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

function scoreTone(score) {
  return score >= 80 ? 'good' : 'watch';
}

function formatDate(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
}

function HistoryPage({ onNavigate, onBack, token, selectedChildId, onSelectChild }) {
  const [children, setChildren] = useState([]);
  const [activeChildId, setActiveChildId] = useState(selectedChildId);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [records, setRecords] = useState([]);
  const [newChildName, setNewChildName] = useState('');
  const [isLoadingChildren, setIsLoadingChildren] = useState(true);
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setIsLoadingChildren(false);
      return undefined;
    }
    let cancelled = false;
    apiFetch('/api/children', { token })
      .then((data) => {
        if (cancelled) return;
        const list = data.children || [];
        setChildren(list);
        if (list.length > 0) {
          const nextId = list.some((child) => child.id === selectedChildId) ? selectedChildId : list[0].id;
          setActiveChildId(nextId);
          onSelectChild(nextId);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingChildren(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, selectedChildId, onSelectChild]);

  useEffect(() => {
    if (!token || activeChildId == null) {
      setRecords([]);
      return undefined;
    }
    let cancelled = false;
    setIsLoadingRecords(true);
    apiFetch(`/api/history?child_id=${activeChildId}`, { token })
      .then((data) => {
        if (!cancelled) setRecords(data.records || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingRecords(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, activeChildId]);

  const handleAddChild = async (event) => {
    event.preventDefault();
    const name = newChildName.trim();
    if (!name) return;

    try {
      const child = await apiFetch('/api/children', {
        token,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      setChildren((prev) => [...prev, child]);
      setActiveChildId(child.id);
      onSelectChild(child.id);
      setNewChildName('');
    } catch (err) {
      setError(err.message);
    }
  };

  const selectedChild = children.find((child) => child.id === activeChildId);

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('mypage'))}>
            ← 뒤로
          </button>
          <h1>촬영 히스토리</h1>
          <span className="mypage-top-space" />
        </div>

        {isLoadingChildren && (
          <p className="subtext" style={{ textAlign: 'center', marginTop: 40 }}>불러오는 중이에요...</p>
        )}

        {!isLoadingChildren && children.length === 0 && (
          <form className="child-add-form" onSubmit={handleAddChild}>
            <p className="subtext" style={{ marginTop: 0 }}>등록된 자녀가 없어요. 먼저 추가해 주세요.</p>
            <label className="input-group">
              <span>자녀 이름</span>
              <input
                type="text"
                value={newChildName}
                onChange={(event) => setNewChildName(event.target.value)}
                placeholder="예: 지우"
              />
            </label>
            <button type="submit" className="login-button">자녀 추가</button>
          </form>
        )}

        {!isLoadingChildren && children.length > 0 && (
          <>
            <div className="child-selector">
              <button
                type="button"
                className="child-selector-trigger"
                onClick={() => setIsDropdownOpen((open) => !open)}
              >
                <span className="child-avatar">{selectedChild?.name?.slice(0, 1)}</span>
                <span className="child-selector-name">{selectedChild?.name}</span>
                <span className="child-selector-arrow" aria-hidden="true">⌄</span>
              </button>

              {isDropdownOpen && (
                <div className="child-selector-menu">
                  {children.map((child) => (
                    <button
                      type="button"
                      key={child.id}
                      className={`child-selector-item ${child.id === activeChildId ? 'active' : ''}`}
                      onClick={() => {
                        setActiveChildId(child.id);
                        onSelectChild(child.id);
                        setIsDropdownOpen(false);
                      }}
                    >
                      <span className="child-avatar small">{child.name.slice(0, 1)}</span>
                      {child.name}
                    </button>
                  ))}
                  <form className="child-add-inline" onSubmit={handleAddChild}>
                    <input
                      type="text"
                      value={newChildName}
                      onChange={(event) => setNewChildName(event.target.value)}
                      placeholder="자녀 이름 추가"
                    />
                    <button type="submit">추가</button>
                  </form>
                </div>
              )}
            </div>

            {isLoadingRecords && (
              <p className="subtext" style={{ textAlign: 'center', marginTop: 30 }}>기록을 불러오는 중이에요...</p>
            )}

            {!isLoadingRecords && records.length === 0 && (
              <p className="subtext" style={{ textAlign: 'center', marginTop: 30 }}>
                아직 촬영 기록이 없어요.
              </p>
            )}

            {!isLoadingRecords && records.length > 0 && (
              <ul className="history-list">
                {records.map((record) => (
                  <li className="history-item" key={record.id}>
                    <div className="history-meta">
                      <strong>{formatDate(record.created_at)}</strong>
                      <span>충치 의심 {record.cavity_count}곳</span>
                    </div>
                    <span className={`history-badge ${scoreTone(record.score)}`}>{record.score}점</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}

        {error && (
          <p className="social-error" role="alert" style={{ textAlign: 'center', marginTop: 20 }}>{error}</p>
        )}
      </div>
    </section>
  );
}

export default HistoryPage;
