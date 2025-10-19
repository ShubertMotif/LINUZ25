visits_data['visitors'].append(visitor_info)
if len(visits_data['visitors']) > 100:
    visits_data['visitors'] = visits_data['visitors'][-100:]
save_visits(visits_data)

if current_user.is_authenticated:
    blockchain.reward_user(current_user, blockchain.refresh_reward, 'refresh')

return render_template('index.html', visit_count=visits_data['count'], current_user=current_user)


@app.route('/stats')
@login_required
def stats():
    visits_data = load_visits()
    return render_template('stats.html',
                           visit_count=visits_data['count'],
                           recent_visitors=visits_data['visitors'][-10:],
                           current_user=current_user)


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("Username già registrato.")
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.flush()

        new_user.wallet_address = blockchain.generate_wallet_address(new_user.id)
        blockchain.reward_user(new_user, blockchain.registration_reward, 'registration')

        flash(f"Registrazione completata! Ricevuti {blockchain.registration_reward} ADG di benvenuto!")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)
            blockchain.reward_user(user, blockchain.login_reward, 'login')
            flash(f"Login effettuato! Ricevuto {blockchain.login_reward} ADG!")
            return redirect(url_for('index'))
        else:
            flash("Credenziali errate.")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principale con progetti"""
    user_projects = get_user_projects(current_user)
    return render_template('dashboard.html',
                           projects=user_projects,
                           current_user=current_user)


# =============================================================================
# BLOCKCHAIN ROUTES
# =============================================================================

@app.route('/wallet')
@login_required
def wallet():
    """Dashboard wallet personale ADG"""
    if not current_user.wallet_address:
        current_user.wallet_address = blockchain.generate_wallet_address(current_user.id)
        db.session.commit()

    transactions = Transaction.query.filter_by(to_wallet=current_user.wallet_address) \
        .order_by(Transaction.timestamp.desc()) \
        .limit(20).all()

    wallet_data = {
        'balance': current_user.balance,
        'wallet_address': current_user.wallet_address,
        'created_at': current_user.created_at
    }

    return render_template('wallet.html',
                           wallet=wallet_data,
                           transactions=transactions,
                           current_user=current_user)


@app.route('/mining')
@login_required
def mining():
    """Dashboard mining ADG"""
    user_miners = MiningSession.query.filter_by(user_id=current_user.id).all()
    mining_stats = blockchain.get_mining_stats()

    return render_template('mining.html',
                           miners=user_miners,
                           mining_stats=mining_stats,
                           current_user=current_user)


# =============================================================================
# FILE MANAGEMENT ROUTES
# =============================================================================

@app.route('/files')
@login_required
def files_dashboard():
    """Dashboard file utente"""
    user_files = UserFile.query.filter_by(user_id=current_user.id) \
        .order_by(UserFile.uploaded_at.desc()).all()

    total_files = len(user_files)
    total_size = sum(f.file_size for f in user_files)

    files_by_type = {}
    for file in user_files:
        if file.file_type not in files_by_type:
            files_by_type[file.file_type] = []
        files_by_type[file.file_type].append(file)

    return render_template('files_dashboard.html',
                           files=user_files,
                           files_by_type=files_by_type,
                           total_files=total_files,
                           total_size=total_size,
                           current_user=current_user)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """Upload singolo file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Tipo file non consentito'})

        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        file_type = get_file_type(original_filename)

        user_file = UserFile(
            user_id=current_user.id,
            filename=safe_filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            mime_type=file.mimetype
        )

        db.session.add(user_file)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'File caricato con successo',
            'file_id': user_file.id,
            'filename': original_filename,
            'file_type': file_type,
            'file_size': file_size
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    """Download file"""
    file_record = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()

    if not file_record:
        flash('File non trovato')
        return redirect(url_for('files_dashboard'))

    try:
        return send_file(
            file_record.file_path,
            as_attachment=True,
            download_name=file_record.original_filename,
            mimetype=file_record.mime_type
        )
    except FileNotFoundError:
        flash('File fisico non trovato')
        return redirect(url_for('files_dashboard'))


@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """Elimina file"""
    file_record = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()

    if not file_record:
        return jsonify({'success': False, 'message': 'File non trovato'})

    try:
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)

        db.session.delete(file_record)
        db.session.commit()

        return jsonify({'success': True, 'message': 'File eliminato'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


# =============================================================================
# NOTES MANAGEMENT ROUTES
# =============================================================================

@app.route('/notes')
@login_required
def notes_dashboard():
    """Dashboard note utente"""
    note_type = request.args.get('type', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')

    query = UserNote.query.filter_by(user_id=current_user.id)

    if note_type:
        query = query.filter_by(note_type=note_type)
    if priority:
        query = query.filter_by(priority=priority)
    if search:
        query = query.filter(UserNote.title.contains(search) |
                             UserNote.content.contains(search))

    notes = query.order_by(UserNote.updated_at.desc()).all()

    total_notes = UserNote.query.filter_by(user_id=current_user.id).count()
    completed_tasks = UserNote.query.filter_by(
        user_id=current_user.id, note_type='task', completed=True
    ).count()
    pending_tasks = UserNote.query.filter_by(
        user_id=current_user.id, note_type='task', completed=False
    ).count()

    return render_template('notes_dashboard.html',
                           notes=notes,
                           total_notes=total_notes,
                           completed_tasks=completed_tasks,
                           pending_tasks=pending_tasks,
                           current_user=current_user)


@app.route('/create_note', methods=['GET', 'POST'])
@login_required
def create_note():
    """Crea nuova nota"""
    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            note = UserNote(
                user_id=current_user.id,
                title=data.get('title'),
                content=data.get('content'),
                note_type=data.get('note_type', 'text'),
                priority=data.get('priority', 'normal'),
                tags=data.get('tags', ''),
                external_url=data.get('external_url', '')
            )

            db.session.add(note)
            db.session.commit()

            blockchain.reward_user(current_user, 1.0, 'note_created')

            flash('Nota creata con successo! (+1 ADG)', 'success')

            if request.is_json:
                return jsonify({'success': True, 'message': 'Nota creata', 'note_id': note.id})
            else:
                return redirect(url_for('notes_dashboard'))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore: {str(e)}', 'error')
                return redirect(url_for('notes_dashboard'))

    return render_template('create_note.html', current_user=current_user)


@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Elimina nota"""
    note = UserNote.query.filter_by(id=note_id, user_id=current_user.id).first()

    if not note:
        return jsonify({'success': False, 'message': 'Nota non trovata'})

    try:
        db.session.delete(note)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Nota eliminata'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


# =============================================================================
# PROGETTI ROUTES (NUOVO)
# =============================================================================

@app.route('/projects')
@login_required
def projects_list():
    """Lista progetti accessibili dall'utente"""
    user_projects = get_user_projects(current_user)

    return render_template('projects_list.html',
                           projects=user_projects,
                           current_user=current_user)


@app.route('/project/<int:project_id>')
@login_required
@project_access_required('view')
def project_detail(project_id):
    """Dettaglio progetto"""
    project = Project.query.get_or_404(project_id)

    members = ProjectMember.query.filter_by(project_id=project_id).all()

    project_files = UserFile.query.filter_by(project_id=project_id) \
        .order_by(UserFile.uploaded_at.desc()).all()

    project_notes = UserNote.query.filter_by(project_id=project_id) \
        .order_by(UserNote.updated_at.desc()).all()

    user_role = 'owner' if project.owner_id == current_user.id else None
    if not user_role:
        member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first()
        user_role = member.role_in_project if member else 'viewer'

    stats = {
        'members_count': len(members),
        'files_count': len(project_files),
        'notes_count': len(project_notes),
        'recent_activity_count': 0
    }

    return render_template('project_detail.html',
                           project=project,
                           members=members,
                           files=project_files,
                           notes=project_notes,
                           user_role=user_role,
                           stats=stats,
                           current_user=current_user)


@app.route('/project/create', methods=['GET', 'POST'])
@login_required
@can_create_projects
def create_project():
    """Crea nuovo progetto (solo admin e role_a)"""
    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            name = data.get('name')
            description = data.get('description', '')

            if not name:
                return jsonify({'success': False, 'message': 'Nome progetto obbligatorio'})

            project = Project(
                name=name,
                description=description,
                owner_id=current_user.id,
                status='active'
            )

            db.session.add(project)
            db.session.commit()

            blockchain.reward_user(current_user, 5.0, 'project_created')

            flash(f'Progetto "{name}" creato con successo! (+5 ADG)', 'success')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Progetto creato con successo',
                    'project_id': project.id,
                    'redirect': url_for('project_detail', project_id=project.id)
                })
            else:
                return redirect(url_for('project_detail', project_id=project.id))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore nella creazione: {str(e)}', 'error')
                return redirect(url_for('projects_list'))

    return render_template('create_project.html', current_user=current_user)


@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_access_required('admin')
def edit_project(project_id):
    """Modifica progetto (solo owner)"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            project.name = data.get('name', project.name)
            project.description = data.get('description', project.description)
            project.status = data.get('status', project.status)
            project.updated_at = datetime.utcnow()

            db.session.commit()

            notify_project_members(
                project,
                'project_updated',
                f'Progetto "{project.name}" aggiornato',
                'Il progetto è stato modificato dal proprietario',
                exclude_user_id=current_user.id
            )

            flash('Progetto aggiornato con successo!', 'success')

            if request.is_json:
                return jsonify({'success': True, 'message': 'Progetto aggiornato'})
            else:
                return redirect(url_for('project_detail', project_id=project_id))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore: {str(e)}', 'error')
                return redirect(url_for('project_detail', project_id=project_id))

    return render_template('edit_project.html', project=project, current_user=current_user)


@app.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
@project_access_required('admin')
def delete_project(project_id):
    """Elimina progetto (solo owner o admin)"""
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name

        notify_project_members(
            project,
            'project_deleted',
            f'Progetto "{project_name}" eliminato',
            'Il progetto è stato eliminato dal proprietario',
            exclude_user_id=current_user.id
        )

        db.session.delete(project)
        db.session.commit()

        flash(f'Progetto "{project_name}" eliminato con successo.', 'success')

        if request.is_json:
            return jsonify({'success': True, 'message': 'Progetto eliminato'})
        else:
            return redirect(url_for('projects_list'))

    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
        else:
            flash(f'Errore: {str(e)}', 'error')
            return redirect(url_for('projects_list'))


@app.route('/project/<int:project_id>/add_member', methods=['POST'])
@login_required
@project_access_required('admin')
def add_project_member(project_id):
    """Aggiunge membro al progetto"""
    try:
        data = request.get_json() or request.form

        user_id = data.get('user_id')
        role_in_project = data.get('role', 'viewer')

        if not user_id:
            return jsonify({'success': False, 'message': 'Utente non specificato'})

        if role_in_project not in ['collaborator', 'viewer']:
            role_in_project = 'viewer'

        success, message, member = add_member_to_project(project_id, user_id, role_in_project)

        if success:
            project = Project.query.get(project_id)
            user = User.query.get(user_id)
            notify_project_members(
                project,
                'member_added',
                f'Nuovo membro aggiunto: {user.username}',
                f'{user.username} è stato aggiunto come {member.get_role_display()}',
                exclude_user_id=user_id
            )

            flash(message, 'success')
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/project/<int:project_id>/remove_member/<int:user_id>', methods=['POST'])
@login_required
@project_access_required('admin')
def remove_project_member(project_id, user_id):
    """Rimuove membro dal progetto"""
    try:
        success, message = remove_member_from_project(project_id, user_id)

        if success:
            project = Project.query.get(project_id)
            create_notification(
                user_id=user_id,
                notification_type='member_removed',
                title=f'Rimosso dal progetto: {project.name}',
                message='Sei stato rimosso da questo progetto',
                project_id=project_id
            )

            flash(message, 'success')
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/project/<int:project_id>/upload_file', methods=['POST'])
@login_required
@project_access_required('edit')
def upload_project_file(project_id):
    """Upload file in progetto (solo owner e collaborator)"""
    try:
        project = Project.query.get_or_404(project_id)

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Tipo file non consentito'})

        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        file_type = get_file_type(original_filename)

        user_file = UserFile(
            user_id=current_user.id,
            project_id=project_id,
            filename=safe_filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            mime_type=file.mimetype
        )

        db.session.add(user_file)
        db.session.commit()

        blockchain.reward_user(current_user, 2.0, 'file_upload_project')

        notify_project_members(
            project,
            'file_upload',
            f'Nuovo file in "{project.name}"',
            f'{current_user.username} ha caricato: {original_filename}',
            exclude_user_id=current_user.id
        )

        return jsonify({
            'success': True,
            'message': 'File caricato nel progetto (+2 ADG)',
            'file_id': user_file.id,
            'filename': original_filename
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/project/<int:project_id>/create_note', methods=['GET', 'POST'])
@login_required
@project_access_required('edit')
def create_project_note(project_id):
    """Crea nota in progetto (solo owner e collaborator)"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            note = UserNote(
                user_id=current_user.id,
                project_id=project_id,
                title=data.get('title'),
                content=data.get('content'),
                note_type=data.get('note_type', 'text'),
                priority=data.get('priority', 'normal'),
                tags=data.get('tags', '')
            )

            db.session.add(note)
            db.session.commit()

            blockchain.reward_user(current_user, 1.0, 'note_created_project')

            notify_project_members(
                project,
                'note_added',
                f'Nuova nota in "{project.name}"',
                f'{current_user.username} ha creato: {note.title}',
                exclude_user_id=current_user.id
            )

            flash('Nota creata con successo! (+1 ADG)', 'success')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Nota creata',
                    'note_id': note.id
                })
            else:
                return redirect(url_for('project_detail', project_id=project_id))

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore: {str(e)}', 'error')
                return redirect(url_for('project_detail', project_id=project_id))

    return render_template('create_project_note.html',
                           project=project,
                           current_user=current_user)


@app.route('/project/note/<int:note_id>/comment', methods=['POST'])
@login_required
def add_note_comment(note_id):
    """Aggiungi commento a nota (tutti i membri possono commentare)"""
    try:
        note = UserNote.query.get_or_404(note_id)

        if note.project_id:
            project = Project.query.get(note.project_id)
            if not project.can_user_view(current_user.id):
                return jsonify({'success': False, 'message': 'Accesso negato'})

        data = request.get_json() or request.form
        content = data.get('content')

        if not content:
            return jsonify({'success': False, 'message': 'Contenuto commento mancante'})

        comment = NoteComment(
            note_id=note_id,
            user_id=current_user.id,
            content=content
        )

        db.session.add(comment)
        db.session.commit()

        if note.user_id != current_user.id:
            create_notification(
                user_id=note.user_id,
                notification_type='note_comment',
                title=f'Nuovo commento su: {note.title}',
                message=f'{current_user.username} ha commentato la tua nota',
                link=url_for('project_detail', project_id=note.project_id),
                project_id=note.project_id
            )

        return jsonify({
            'success': True,
            'message': 'Commento aggiunto',
            'comment': {
                'id': comment.id,
                'username': current_user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


# =============================================================================
# NOTIFICHE ROUTES (NUOVO)
# =============================================================================

@app.route('/notifications')
@login_required
def notifications_list():
    """Lista notifiche utente"""
    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()) \
        .limit(50).all()

    return render_template('notifications.html',
                           notifications=notifications,
                           current_user=current_user)


@app.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Segna notifica come letta"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first_or_404()

        notification.mark_as_read()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read_route():
    """Segna tutte notifiche come lette"""
    try:
        mark_all_notifications_read(current_user.id)
        return jsonify({'success': True, 'message': 'Tutte le notifiche segnate come lette'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =============================================================================
# SERVICE ROUTES
# =============================================================================

@app.route('/life-science')
def life_science():
    return render_template('life_science.html', current_user=current_user)


@app.route('/servizi-informatici')
def servizi_informatici():
    return render_template('servizi_informatici.html', current_user=current_user)


@app.route('/difesa')
def difesa():
    return render_template('difesa.html', current_user=current_user)


@app.route('/finanza')
def finanza():
    return render_template('finanza.html', current_user=current_user)


@app.route('/chi-siamo')
def chi_siamo():
    return render_template('chi_siamo.html', current_user=current_user)


@app.route('/contatti')
def contatti():
    return render_template('contatti.html', current_user=current_user)


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_db():
    """Inizializza database se necessario"""
    try:
        db.create_all()
        print("✅ Database inizializzato")
        print(f"Mining Pool RTX3060: {'ATTIVO' if blockchain.mining_pool.is_active else 'DISATTIVO'}")
        return True
    except Exception as e:
        print(f"❌ Errore inizializzazione database: {e}")
        return False


# Inizializza database all'avvio dell'app
with app.app_context():
    init_db()

# =============================================================================
# WSGI APPLICATION OBJECT
# =============================================================================

application = app

# =============================================================================
# MAIN (per sviluppo locale)
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("ADELCHI GROUP - SISTEMA PROGETTI INTEGRATO")
    print("=" * 70)
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Mining Pool RTX3060: {'ATTIVO' if blockchain.mining_pool.is_active else 'DISATTIVATO'}")
    print(f"Current Block Height: {blockchain.current_block_height}")
    print(f"Upload Folder: {UPLOAD_FOLDER}")
    print("\n🎯 Funzionalità Integrate:")
    print("  ✅ Sistema Ruoli (Admin, Manager, Collaboratore, Utente)")
    print("  ✅ Progetti Condivisi con Team")
    print("  ✅ File Management per Progetto")
    print("  ✅ Note Collaborative con Commenti")
    print("  ✅ Sistema Notifiche")
    print("  ✅ Blockchain ADG Token")
    print("  ✅ API Mobile JWT")
    print("\n📝 Per produzione utilizzare Gunicorn")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0',
            port=5000)  # =============================================================================
# ADELCHI GROUP - APPLICAZIONE FLASK COMPLETA CON SISTEMA PROGETTI
# File: app2.py
# Versione: 2.0 - Sistema Progetti Integrato
# =============================================================================

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import json
import os
import hashlib
import uuid
import time
import threading
import queue
import jwt
from datetime import datetime, timedelta
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersegreto'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///adelchi_complete.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip',
                      'rar', 'mp4', 'mp3', 'wav'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# JWT Configuration
JWT_SECRET = 'your-secret-key-here-change-in-production'
JWT_ALGORITHM = 'HS256'

# Create folders if they don't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists('static'):
    os.makedirs('static')

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# =============================================================================
# DATABASE MODELS - BASE
# =============================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    wallet_address = db.Column(db.String(200), unique=True, nullable=True)
    balance = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='role_c', nullable=False)  # NUOVO: Sistema ruoli

    def get_role_display(self):
        """Nome leggibile del ruolo"""
        role_names = {
            'admin': 'Amministratore',
            'role_a': 'Manager',
            'role_b': 'Collaboratore',
            'role_c': 'Utente Base'
        }
        return role_names.get(self.role, 'Utente')

    def can_create_projects(self):
        """Verifica se può creare progetti"""
        return self.role in ['admin', 'role_a']

    def can_manage_user(self, target_user):
        """Verifica se può gestire un altro utente"""
        return UserRole.can_manage(self.role, target_user.role)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(64), unique=True, nullable=False)
    from_wallet = db.Column(db.String(200), nullable=True)
    to_wallet = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    block_height = db.Column(db.Integer, nullable=True)
    confirmed = db.Column(db.Boolean, default=True)


class MiningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    miner_name = db.Column(db.String(100), nullable=False)
    gpu_model = db.Column(db.String(50), nullable=False)
    hashrate = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_ping = db.Column(db.DateTime, default=datetime.utcnow)


class UserFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)  # NUOVO
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='files')

    def is_shared(self):
        """Verifica se file è condiviso in un progetto"""
        return self.project_id is not None


class UserNote(db.Model):
    __tablename__ = 'user_notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)  # NUOVO
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='text')
    priority = db.Column(db.String(20), default='normal')
    completed = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(500), nullable=True)
    external_url = db.Column(db.String(500), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='notes')

    def is_shared(self):
        """Verifica se nota è condivisa in un progetto"""
        return self.project_id is not None


# =============================================================================
# DATABASE MODELS - SISTEMA PROGETTI (NUOVO)
# =============================================================================

class UserRole:
    """Classe helper per gestione ruoli"""
    ADMIN = 'admin'
    ROLE_A = 'role_a'
    ROLE_B = 'role_b'
    ROLE_C = 'role_c'

    @staticmethod
    def get_level(role):
        """Restituisce livello gerarchico (4=max, 1=min)"""
        levels = {'admin': 4, 'role_a': 3, 'role_b': 2, 'role_c': 1}
        return levels.get(role, 0)

    @staticmethod
    def can_manage(manager_role, target_role):
        """Verifica se manager può gestire target"""
        return UserRole.get_level(manager_role) > UserRole.get_level(target_role)


class Project(db.Model):
    """Progetto condiviso"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

    owner = db.relationship('User', backref='owned_projects', foreign_keys=[owner_id])
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    files = db.relationship('UserFile', backref='project', lazy='dynamic')
    notes = db.relationship('UserNote', backref='project', lazy='dynamic')

    def get_member_count(self):
        return self.members.count()

    def get_file_count(self):
        return self.files.count()

    def get_note_count(self):
        return self.notes.count()

    def is_member(self, user_id):
        return self.members.filter_by(user_id=user_id).first() is not None

    def get_user_role(self, user_id):
        member = self.members.filter_by(user_id=user_id).first()
        return member.role_in_project if member else None

    def can_user_edit(self, user_id):
        if self.owner_id == user_id:
            return True
        role = self.get_user_role(user_id)
        return role in ['owner', 'collaborator']

    def can_user_view(self, user_id):
        return self.is_member(user_id) or self.owner_id == user_id


class ProjectMember(db.Model):
    """Membri del progetto"""
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_in_project = db.Column(db.String(20), default='viewer')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='project_memberships')

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),)

    def get_role_display(self):
        roles = {'owner': 'Proprietario', 'collaborator': 'Collaboratore', 'viewer': 'Visualizzatore'}
        return roles.get(self.role_in_project, 'Membro')

    def can_edit(self):
        return self.role_in_project in ['owner', 'collaborator']

    def can_comment(self):
        return True

    def can_upload(self):
        return self.role_in_project in ['owner', 'collaborator']


class Notification(db.Model):
    """Sistema notifiche"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

    def mark_as_read(self):
        self.is_read = True
        db.session.commit()


class NoteComment(db.Model):
    """Commenti alle note"""
    __tablename__ = 'note_comments'

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('user_notes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='comments')
    note = db.relationship('UserNote', backref='comments')


# =============================================================================
# BLOCKCHAIN SYSTEM
# =============================================================================

class MiningPool:
    def __init__(self):
        self.is_active = False
        self.connected_gpus = []
        self.total_hashrate = 0.0
        self.websocket_enabled = True
        self.mining_thread = None
        self.stop_flag = False

    def start_mining(self):
        self.is_active = True
        print("🚀 Mining Pool RTX3060 ATTIVATO")

    def stop_mining(self):
        self.is_active = False
        self.stop_flag = True
        print("🛑 Mining Pool RTX3060 DISATTIVATO")


class BlockchainSystem:
    def __init__(self):
        self.current_block_height = 0
        self.mining_reward = 10.0
        self.registration_reward = 10.0
        self.login_reward = 1.0
        self.refresh_reward = 0.01
        self.mining_pool = MiningPool()

    def generate_wallet_address(self, user_id):
        raw = f"ADG-{user_id}-{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:42]

    def reward_user(self, user, amount, source='unknown'):
        if not user.wallet_address:
            user.wallet_address = self.generate_wallet_address(user.id)

        user.balance += amount
        user.total_earned += amount

        tx_hash = hashlib.sha256(f"{user.wallet_address}-{amount}-{time.time()}".encode()).hexdigest()
        transaction = Transaction(
            tx_hash=tx_hash,
            from_wallet='SYSTEM',
            to_wallet=user.wallet_address,
            amount=amount,
            tx_type=source
        )

        db.session.add(transaction)
        db.session.commit()
        return transaction

    def mine_block(self, miner_address):
        if self.mining_pool.is_active:
            reward = self.mining_reward
        else:
            reward = self.mining_reward * 0.1

        self.current_block_height += 1
        return reward

    def get_mining_stats(self):
        return {
            'pool_active': self.mining_pool.is_active,
            'connected_gpus': len(self.mining_pool.connected_gpus),
            'total_hashrate': self.mining_pool.total_hashrate,
            'current_block': self.current_block_height,
            'websocket_enabled': self.mining_pool.websocket_enabled
        }


blockchain = BlockchainSystem()

# =============================================================================
# VISIT COUNTER SYSTEM
# =============================================================================

VISITS_FILE = 'visits.json'


def load_visits():
    if os.path.exists(VISITS_FILE):
        try:
            with open(VISITS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'count': 0, 'visitors': []}
    return {'count': 0, 'visitors': []}


def save_visits(visits_data):
    with open(VISITS_FILE, 'w') as f:
        json.dump(visits_data, f, indent=2)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return 'image'
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'xls', 'xlsx', 'ppt', 'pptx']:
        return 'document'
    elif ext in ['mp4', 'avi', 'mov', 'wmv']:
        return 'video'
    elif ext in ['mp3', 'wav', 'flac', 'ogg']:
        return 'audio'
    else:
        return 'other'


def _get_gpu_hashrate(gpu_model):
    hashrates = {
        'rtx4090': 120.0, 'rtx4080': 95.0, 'rtx4070': 75.0,
        'rtx3090': 85.0, 'rtx3080': 70.0, 'rtx3070': 55.0,
        'rtx3060': 45.0, 'rx7900xt': 80.0, 'rx6800xt': 65.0
    }
    return hashrates.get(gpu_model.lower(), 30.0)


def generate_token(user_id):
    payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload['user_id']
    except:
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token mancante'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'success': False, 'message': 'Token invalido'}), 401

        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'success': False, 'message': 'Utente non trovato'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =============================================================================
# DECORATORI PERMESSI (NUOVO)
# =============================================================================

def role_required(*roles):
    """Decoratore che verifica ruolo utente"""

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('Non hai i permessi per accedere a questa pagina.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """Decoratore che richiede ruolo admin"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Accesso riservato agli amministratori.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def can_create_projects(f):
    """Decoratore che verifica se può creare progetti"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['admin', 'role_a']:
            flash('Solo Manager e Admin possono creare progetti.', 'error')
            return redirect(url_for('projects_list'))
        return f(*args, **kwargs)

    return decorated_function


def project_access_required(permission_level='view'):
    """Decoratore che verifica accesso a progetto"""

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            project_id = kwargs.get('project_id') or kwargs.get('id')

            if not project_id:
                flash('Progetto non specificato.', 'error')
                return redirect(url_for('projects_list'))

            project = Project.query.get_or_404(project_id)

            if current_user.role == 'admin':
                return f(*args, **kwargs)

            if project.owner_id == current_user.id:
                return f(*args, **kwargs)

            member = ProjectMember.query.filter_by(
                project_id=project_id,
                user_id=current_user.id
            ).first()

            if not member:
                flash('Non hai accesso a questo progetto.', 'error')
                return redirect(url_for('projects_list'))

            if permission_level == 'view':
                return f(*args, **kwargs)
            elif permission_level == 'edit':
                if member.role_in_project in ['owner', 'collaborator']:
                    return f(*args, **kwargs)
                else:
                    flash('Non hai i permessi per modificare questo progetto.', 'error')
                    return redirect(url_for('project_detail', project_id=project_id))
            elif permission_level == 'admin':
                flash('Solo il proprietario può eseguire questa azione.', 'error')
                return redirect(url_for('project_detail', project_id=project_id))

            flash('Permessi insufficienti.', 'error')
            return redirect(url_for('projects_list'))

        return decorated_function

    return decorator


# =============================================================================
# HELPER FUNCTIONS - NOTIFICHE (NUOVO)
# =============================================================================

def create_notification(user_id, notification_type, title, message=None, link=None, project_id=None):
    """Crea notifica per utente"""
    try:
        notification = Notification(
            user_id=user_id,
            project_id=project_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        print(f"Errore creazione notifica: {e}")
        db.session.rollback()
        return None


def notify_project_members(project, notification_type, title, message=None, exclude_user_id=None):
    """Invia notifica a tutti i membri progetto"""
    members = project.members.all()

    for member in members:
        if exclude_user_id and member.user_id == exclude_user_id:
            continue

        create_notification(
            user_id=member.user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=url_for('project_detail', project_id=project.id),
            project_id=project.id
        )

    if project.owner_id != exclude_user_id:
        create_notification(
            user_id=project.owner_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=url_for('project_detail', project_id=project.id),
            project_id=project.id
        )


def get_user_unread_notifications_count(user_id):
    """Conta notifiche non lette"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_all_notifications_read(user_id):
    """Segna tutte notifiche come lette"""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()


# =============================================================================
# HELPER FUNCTIONS - GESTIONE PROGETTI (NUOVO)
# =============================================================================

def get_user_projects(user):
    """Ottiene tutti i progetti dell'utente categorizzati"""
    owned = Project.query.filter_by(owner_id=user.id, status='active').all()

    memberships = ProjectMember.query.filter_by(user_id=user.id).all()

    collaborating = []
    viewing = []

    for membership in memberships:
        if membership.project.status == 'active':
            if membership.role_in_project == 'collaborator':
                collaborating.append(membership.project)
            elif membership.role_in_project == 'viewer':
                viewing.append(membership.project)

    return {
        'owned': owned,
        'collaborating': collaborating,
        'viewing': viewing,
        'total': len(owned) + len(collaborating) + len(viewing)
    }


def add_member_to_project(project_id, user_id, role_in_project='viewer'):
    """Aggiunge membro a progetto"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return False, "Progetto non trovato", None

        user = User.query.get(user_id)
        if not user:
            return False, "Utente non trovato", None

        existing = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()

        if existing:
            return False, "Utente già membro del progetto", None

        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role_in_project=role_in_project
        )

        db.session.add(member)
        db.session.commit()

        create_notification(
            user_id=user_id,
            notification_type='project_invite',
            title=f'Aggiunto al progetto: {project.name}',
            message=f'Sei stato aggiunto come {member.get_role_display()}',
            link=url_for('project_detail', project_id=project_id),
            project_id=project_id
        )

        return True, "Membro aggiunto con successo", member

    except Exception as e:
        db.session.rollback()
        return False, f"Errore: {str(e)}", None


def remove_member_from_project(project_id, user_id):
    """Rimuove membro da progetto"""
    try:
        member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()

        if not member:
            return False, "Membro non trovato"

        db.session.delete(member)
        db.session.commit()

        return True, "Membro rimosso con successo"

    except Exception as e:
        db.session.rollback()
        return False, f"Errore: {str(e)}"


def update_member_role(project_id, user_id, new_role):
    """Aggiorna ruolo membro"""
    try:
        member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()

        if not member:
            return False, "Membro non trovato"

        member.role_in_project = new_role
        member.last_activity = datetime.utcnow()
        db.session.commit()

        return True, "Ruolo aggiornato con successo"

    except Exception as e:
        db.session.rollback()
        return False, f"Errore: {str(e)}"


# =============================================================================
# CONTEXT PROCESSOR
# =============================================================================

@app.context_processor
def inject_global_vars():
    """Inietta variabili globali in tutti i template"""
    unread_notifications = 0
    if current_user.is_authenticated:
        unread_notifications = get_user_unread_notifications_count(current_user.id)

    return dict(
        current_user=current_user,
        unread_notifications=unread_notifications,
        UserRole=UserRole
    )


# =============================================================================
# MAIN ROUTES
# =============================================================================

@app.route('/')
def index():
    visits_data = load_visits()
    visits_data['count'] += 1
    visitor_info = {
        'timestamp': datetime.now().isoformat(),
        'ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown')),
        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
        'user': current_user.username if current_user.is_authenticated else 'Anonimo'
    }
    visits_