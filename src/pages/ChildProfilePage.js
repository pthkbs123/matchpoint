import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

function ChildProfilePage({ onNavigate, token, selectedChildId, onSelectChild }) {
  const [children, setChildren] = useState([]);
  const [name, setName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  const loadChildren = () => {
    if (!token) return Promise.resolve();
    setIsLoading(true);
    return apiFetch('/api/children', { token })
      .then((data) => {
        const list = data.children || [];
        setChildren(list);
        if (list.length > 0 && !list.some((child) => child.id === selectedChildId)) {
          onSelectChild(list[0].id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => { loadChildren(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const resetForm = () => {
    setName('');
    setBirthDate('');
    setEditingId(null);
  };

  const startEdit = (child) => {
    setEditingId(child.id);
    setName(child.name);
    setBirthDate(child.birthDate || '');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!name.trim()) return;
    setIsSaving(true);
    setError('');
    try {
      const path = editingId ? `/api/children/${editingId}` : '/api/children';
      const child = await apiFetch(path, {
        token,
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), birthDate: birthDate || null }),
      });
      onSelectChild(child.id);
      resetForm();
      await loadChildren();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={() => onNavigate('mypage')}>← 뒤로</button>
          <h1>자녀 프로필</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="section-intro">
          <span className="section-intro-icon">☺</span>
          <div>
            <h2>누구의 기록인가요?</h2>
            <p>촬영 결과와 리포트는 선택한 자녀 기준으로 저장됩니다.</p>
          </div>
        </div>

        {isLoading ? (
          <p className="subtext page-state">자녀 정보를 불러오는 중이에요...</p>
        ) : (
          <div className="child-profile-list">
            {children.map((child) => (
              <article className={`child-profile-item ${child.id === selectedChildId ? 'selected' : ''}`} key={child.id}>
                <button type="button" className="child-profile-select" onClick={() => onSelectChild(child.id)}>
                  <span className="child-avatar">{child.name.slice(0, 1)}</span>
                  <span>
                    <strong>{child.name}</strong>
                    <small>{child.birthDate || '생년월일 미등록'}</small>
                  </span>
                  <b>{child.id === selectedChildId ? '관리 중' : '선택'}</b>
                </button>
                <button type="button" className="child-edit-button" onClick={() => startEdit(child)}>수정</button>
              </article>
            ))}
          </div>
        )}

        <form className="child-profile-form" onSubmit={handleSubmit}>
          <div className="card-head">
            <h2>{editingId ? '자녀 정보 수정' : '자녀 추가'}</h2>
            {editingId && <button type="button" className="text-button" onClick={resetForm}>취소</button>}
          </div>
          <label className="input-group">
            <span>이름</span>
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="예: 지우" maxLength={20} />
          </label>
          <label className="input-group">
            <span>생년월일 <small>(선택)</small></span>
            <input type="date" value={birthDate} onChange={(event) => setBirthDate(event.target.value)} />
          </label>
          <button type="submit" className="login-button" disabled={isSaving || !name.trim()}>
            {isSaving ? '저장 중...' : editingId ? '수정 내용 저장' : '자녀 등록'}
          </button>
        </form>

        {error && <p className="social-error" role="alert">{error}</p>}
      </div>
    </section>
  );
}

export default ChildProfilePage;
