window.updateQuizProgress = function updateQuizProgress(data) {
    if (typeof data.completed_quizzes === 'number') {
        const completedCount = document.getElementById('quiz-completed-count');
        if (completedCount) {
            completedCount.textContent = data.completed_quizzes;
        }
    }

    if (typeof data.progress_percent === 'number') {
        const progressPercent = document.getElementById('quiz-progress-percent');
        const progressInline = document.getElementById('quiz-progress-inline');
        const progressBar = document.getElementById('quiz-progress-bar');

        if (progressPercent) {
            progressPercent.textContent = `${data.progress_percent}%`;
        }
        if (progressInline) {
            progressInline.textContent = `${data.progress_percent}%`;
        }
        if (progressBar) {
            progressBar.style.width = `${data.progress_percent}%`;
        }
    }
};

window.updateQuizResult = function updateQuizResult(quizId, data) {
    const resultDiv = document.getElementById(`result-quiz-${quizId}`);
    if (!resultDiv) {
        return;
    }

    resultDiv.textContent = data.message;
    resultDiv.className = `mt-5 rounded-2xl px-4 py-3 text-sm font-bold ${data.status === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`;
};

window.isTestQuestionCard = function isTestQuestionCard(card) {
    return Boolean(card?.hasAttribute('data-test-question'));
};

window.updateQuizCardState = function updateQuizCardState(quizId, data, selectedButton) {
    const quizCard = document.querySelector(`[data-quiz-card][data-quiz-id="${quizId}"]`);
    const quizButtons = document.querySelectorAll(`.quiz-answer-button[data-quiz-id="${quizId}"]`);
    const statusBadge = document.getElementById(`quiz-status-${quizId}`);
    const isTestCard = window.isTestQuestionCard(quizCard);

    quizButtons.forEach(button => {
        button.classList.remove('border-red-200', 'bg-red-50', 'text-red-600', 'border-emerald-200', 'bg-emerald-50', 'text-emerald-700');
        button.classList.remove('border-transparent', 'border-white');
        button.classList.add(isTestCard ? 'border-gray-100' : 'border-white');
    });

    if (selectedButton) {
        selectedButton.classList.remove('border-transparent', 'border-white');
        if (data.status === 'success') {
            selectedButton.classList.add('border-emerald-200', 'bg-emerald-50', 'text-emerald-700');
        } else {
            selectedButton.classList.add('border-red-200', 'bg-red-50', 'text-red-600');
        }
    }

    if (quizCard && data.completed) {
        quizCard.dataset.quizCompleted = 'true';
    }

    if (statusBadge) {
        if (data.completed) {
            statusBadge.textContent = isTestCard ? 'Пройдено' : 'Раунд закрыт';
            statusBadge.className = 'inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] bg-emerald-50 text-emerald-600';
        } else if (data.status === 'success') {
            statusBadge.textContent = isTestCard ? 'Верный ответ' : 'Ответ принят';
            statusBadge.className = 'inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] bg-emerald-50 text-emerald-600';
        } else {
            statusBadge.textContent = 'Попробуйте ещё';
            statusBadge.className = 'inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] bg-red-50 text-red-600';
        }
    }

    if (data.completed && !isTestCard) {
        quizButtons.forEach(button => {
            button.disabled = true;
        });
    }
};

window.showTestQuestion = function showTestQuestion(index) {
    const questions = document.querySelectorAll('[data-test-question]');
    const finishScreen = document.getElementById('test-finish-screen');

    questions.forEach(question => {
        question.classList.add('hidden');
    });

    if (finishScreen) {
        finishScreen.classList.add('hidden');
    }

    const activeQuestion = questions[index];
    if (!activeQuestion) {
        if (finishScreen) {
            finishScreen.classList.remove('hidden');
        }
        return;
    }

    activeQuestion.classList.remove('hidden');
    const nextButton = activeQuestion.querySelector('[data-test-next]');
    const hasLockedButtons = Array.from(activeQuestion.querySelectorAll('[data-test-option]')).every(button => button.disabled);

    if (nextButton) {
        nextButton.classList.toggle('hidden', !hasLockedButtons);
    }
};

window.resetTestState = function resetTestState() {
    document.querySelectorAll('[data-test-question]').forEach(question => {
        question.classList.add('hidden');

        question.querySelectorAll('[data-test-option]').forEach(button => {
            button.disabled = false;
            button.classList.remove('border-red-200', 'bg-red-50', 'text-red-600', 'border-emerald-200', 'bg-emerald-50', 'text-emerald-700', 'border-transparent');
            button.classList.add('border-gray-100', 'bg-slate-50', 'text-slate-700');
        });

        const resultDiv = question.querySelector('[id^="result-quiz-"]');
        if (resultDiv) {
            resultDiv.textContent = '';
            resultDiv.className = 'mt-5 hidden rounded-2xl px-4 py-3 text-sm font-bold';
        }

        const nextButton = question.querySelector('[data-test-next]');
        if (nextButton) {
            nextButton.classList.add('hidden');
        }

        const statusBadge = question.querySelector('[id^="quiz-status-"]');
        if (statusBadge) {
            if (question.dataset.quizCompleted === 'true') {
                statusBadge.textContent = 'Пройдено';
                statusBadge.className = 'inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] bg-emerald-50 text-emerald-600';
            } else {
                statusBadge.textContent = 'Ожидает ответа';
                statusBadge.className = 'inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] bg-slate-100 text-slate-500';
            }
        }
    });
};

window.initTestWorkspace = function initTestWorkspace() {
    const workspace = document.querySelector('[data-test-workspace]');
    const introScreen = document.getElementById('test-intro-screen');
    const runner = document.getElementById('test-runner');
    const startButton = document.getElementById('start-test-button');
    const restartButton = document.getElementById('restart-test-button');

    if (!workspace || !introScreen || !runner || !startButton) {
        return;
    }

    const startTest = () => {
        introScreen.classList.add('hidden');
        runner.classList.remove('hidden');
        window.resetTestState();
        window.showTestQuestion(0);
    };

    startButton.addEventListener('click', startTest);

    if (restartButton) {
        restartButton.addEventListener('click', startTest);
    }

    document.querySelectorAll('[data-test-next]').forEach(button => {
        button.addEventListener('click', () => {
            const currentQuestion = button.closest('[data-test-question]');
            const currentIndex = Number(currentQuestion?.dataset.index || 0);
            window.showTestQuestion(currentIndex + 1);
        });
    });
};

window.submitQuiz = function submitQuiz(button) {
    const quizId = button.dataset.quizId;
    const answer = button.dataset.quizAnswer;
    const formData = new FormData();
    formData.append('quiz_id', quizId);
    formData.append('answer', answer);

    button.disabled = true;
    const quizCard = button.closest('[data-quiz-card]');
    const isTestCard = window.isTestQuestionCard(quizCard);

    fetch('/quiz', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            window.updateQuizResult(quizId, data);
            window.updateQuizCardState(quizId, data, button);
            window.updateQuizProgress(data);

            if (isTestCard && quizCard) {
                quizCard.querySelectorAll('[data-test-option]').forEach(option => {
                    option.disabled = true;
                });
                const nextButton = quizCard.querySelector('[data-test-next]');
                if (nextButton) {
                    nextButton.classList.remove('hidden');
                }
            }
        })
        .catch(error => {
            window.updateQuizResult(quizId, {
                status: 'error',
                message: 'Не удалось отправить ответ. Попробуйте ещё раз.'
            });
            console.error('Error submitting quiz:', error);
        })
        .finally(() => {
            if (!isTestCard && button.closest('[data-quiz-card]')?.dataset.quizCompleted !== 'true') {
                button.disabled = false;
            }
        });
};

window.initQuizInteractions = function initQuizInteractions() {
    document.querySelectorAll('.quiz-answer-button').forEach(button => {
        button.addEventListener('click', () => {
            window.submitQuiz(button);
        });
    });

    window.initTestWorkspace();
};
