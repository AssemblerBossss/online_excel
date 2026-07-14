import React, {useEffect, useState} from 'react';
import {permissionsAPI, TablePermission} from '../api/permissions';
import {colors, rounded, shadowLevel2, spacing, typography} from '../styles/theme';

interface Props {
    tableId: number;
}

const emptyForm = {email: '', can_read: true, can_write: false, can_manage: false};

const TablePermissionsPanel: React.FC<Props> = ({tableId}) => {
    const [permissions, setPermissions] = useState<TablePermission[]>([]);
    const [visible, setVisible] = useState(true);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [form, setForm] = useState(emptyForm);
    const [granting, setGranting] = useState(false);

    const load = async () => {
        try {
            setLoading(true);
            const data = await permissionsAPI.list(tableId);
            setPermissions(data);
        } catch (err: any) {
            if (err.response?.status === 403) {
                setVisible(false);
            } else {
                setError('Не удалось загрузить список доступа');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [tableId]);

    const handleToggle = async (perm: TablePermission, field: 'can_read' | 'can_write' | 'can_manage') => {
        const prev = permissions;
        const next = {...perm, [field]: !perm[field]};
        setPermissions(list => list.map(p => (p.id === perm.id ? next : p)));
        try {
            await permissionsAPI.update(tableId, perm.user_id, {[field]: next[field]});
        } catch (err) {
            setPermissions(prev);
            setError('Не удалось изменить права');
        }
    };

    const handleRevoke = async (perm: TablePermission) => {
        const prev = permissions;
        setPermissions(list => list.filter(p => p.id !== perm.id));
        try {
            await permissionsAPI.revoke(tableId, perm.user_id);
        } catch (err) {
            setPermissions(prev);
            setError('Не удалось убрать доступ');
        }
    };

    const handleGrant = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.email.trim()) return;
        try {
            setGranting(true);
            setError('');
            const created = await permissionsAPI.grant(tableId, form);
            setPermissions(list => [...list, created]);
            setForm(emptyForm);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            setError(detail || 'Не удалось выдать доступ');
        } finally {
            setGranting(false);
        }
    };

    if (loading || !visible) return null;

    return (
        <div style={styles.card}>
            <h2 style={styles.title}>Доступ к таблице</h2>

            <div style={styles.list}>
                {permissions.length === 0 && (
                    <p style={styles.muted}>Ни у кого, кроме вас, нет доступа</p>
                )}
                {permissions.map(perm => (
                    <div key={perm.id} style={styles.row}>
                        <div style={styles.rowHeader}>
                            <span style={styles.email}>{perm.user_email ?? `user #${perm.user_id}`}</span>
                            <button style={styles.revokeBtn} onClick={() => handleRevoke(perm)}
                                    title="Убрать доступ">
                                ×
                            </button>
                        </div>
                        <div style={styles.checks}>
                            {(['can_read', 'can_write', 'can_manage'] as const).map(field => (
                                <label key={field} style={styles.checkLabel}>
                                    <input
                                        type="checkbox"
                                        checked={perm[field]}
                                        onChange={() => handleToggle(perm, field)}
                                    />
                                    {field === 'can_read' ? 'Чтение' : field === 'can_write' ? 'Запись' : 'Управление'}
                                </label>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {error && <p style={styles.error}>{error}</p>}

            <form onSubmit={handleGrant} style={styles.form}>
                <input
                    style={styles.input}
                    type="email"
                    placeholder="Email пользователя"
                    value={form.email}
                    onChange={e => setForm({...form, email: e.target.value})}
                    required
                />
                <div style={styles.checks}>
                    {(['can_read', 'can_write', 'can_manage'] as const).map(field => (
                        <label key={field} style={styles.checkLabel}>
                            <input
                                type="checkbox"
                                checked={form[field]}
                                onChange={e => setForm({...form, [field]: e.target.checked})}
                            />
                            {field === 'can_read' ? 'Чтение' : field === 'can_write' ? 'Запись' : 'Управление'}
                        </label>
                    ))}
                </div>
                <button style={styles.grantBtn} type="submit" disabled={granting}>
                    {granting ? 'Добавление…' : '+ Добавить пользователя'}
                </button>
            </form>
        </div>
    );
};

export default TablePermissionsPanel;

const styles: Record<string, React.CSSProperties> = {
    card: {
        background: colors.canvas,
        borderRadius: rounded.lg,
        padding: spacing.lg,
        boxShadow: shadowLevel2,
    },
    title: {
        ...typography.displaySm,
        color: colors.ink,
        margin: 0,
        marginBottom: spacing.md,
    },
    muted: {
        ...typography.bodySm,
        color: colors.mute,
    },
    list: {
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.sm,
        marginBottom: spacing.md,
    },
    row: {
        padding: spacing.sm,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
    },
    rowHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.xs,
    },
    email: {
        ...typography.bodySmStrong,
        color: colors.ink,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
    revokeBtn: {
        background: 'transparent',
        border: 'none',
        color: colors.mute,
        cursor: 'pointer',
        fontSize: 18,
        lineHeight: 1,
        padding: `0 ${spacing.xxs}px`,
    },
    checks: {
        display: 'flex',
        gap: spacing.sm,
        flexWrap: 'wrap',
    },
    checkLabel: {
        ...typography.caption,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        color: colors.body,
        cursor: 'pointer',
    },
    error: {
        ...typography.bodySm,
        color: colors.errorDeep,
        background: colors.errorSoft,
        padding: spacing.sm,
        borderRadius: rounded.sm,
        marginBottom: spacing.md,
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.sm,
        paddingTop: spacing.md,
        borderTop: `1px solid ${colors.hairline}`,
    },
    input: {
        ...typography.bodySm,
        height: 36,
        padding: `0 ${spacing.sm}px`,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
        outline: 'none',
    },
    grantBtn: {
        ...typography.bodySmStrong,
        height: 36,
        borderRadius: rounded.pill,
        border: 'none',
        background: colors.primary,
        color: colors.onPrimary,
        cursor: 'pointer',
    },
};