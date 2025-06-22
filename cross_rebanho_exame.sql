WITH max_bru AS (
	--Último exame de brucelose
	SELECT 
		eb.nrBrinco as nrBrinco,
		ex.id_exame_pncebt as idExameBru,
		max(ex.dt_colheita_inoculacao) as dtBru
		
	FROM atExameBrinco eb
		JOIN atExame ex on ex.id_exame_pncebt = eb.id_exame_pncebt
	WHERE 
		ResBru <> ''
	GROUP BY
		eb.nrBrinco,
		ex.id_exame_pncebt
	),
	--Último exame de tuberculose
	max_tub AS (
		
		SELECT 
		eb.nrBrinco as nrBrinco,
		ex.id_exame_pncebt as idExameTub,
		max(ex.dt_colheita_inoculacao) as dtTub
		
	FROM atExameBrinco eb
		JOIN atExame ex on ex.id_exame_pncebt = eb.id_exame_pncebt
	WHERE 
		ResTub <> ''
	GROUP BY
		eb.nrBrinco,
		ex.id_exame_pncebt
	
	
	
	),
--Animais adicionados em atestados pela observação, sem resultados de exames
max_obs AS (
		SELECT 
		eb.nrBrinco as nrBrinco,
		ex.id_exame_pncebt as idExameTub,
		max(ex.dt_colheita_inoculacao) as dtTub
		
	FROM atExameBrinco eb
		JOIN atExame ex on ex.id_exame_pncebt = eb.id_exame_pncebt
	WHERE 
		ResTub = ''
			AND ResBru = ''
				AND dsTipoObservacao <> ''
	GROUP BY
		eb.nrBrinco,
		ex.id_exame_pncebt
)


SELECT 
	DISTINCT

	rb.idUnidadeExploracao as 'Código UEP',
	rb.nrBrinco as 'Nº Brinco',
	rb.NrManejo as 'Nº Manejo',
	rb.sexo as 'Sexo',
	rb.Anos,
	rb.Meses,
	rb.dtNasc as 'Data Nasc.',
	CASE
		WHEN STRPTIME(rb.dtRebanho,'%d/%m/%Y') - STRPTIME(rb.dtNasc,'%d/%m/%Y') > INTERVAL 239 DAYS
		THEN 'sim'
		ELSE 'não'
	END as 'Apto Brucelose?',	
	mb.idExameBru as 'Código Atestado Brucelose',
	STRFTIME(mb.dtBru,'%d/%m/%Y') as 'Data Exame Brucelose',
	rmb.ResBru as 'Resultado Brucelose',
	COALESCE(rmb.dsTipoObservacao,obs.dsTipoobservacao,'') as 'Obs. Brucelose',
	CASE
		WHEN STRPTIME(rb.dtRebanho,'%d/%m/%Y') - STRPTIME(rb.dtNasc,'%d/%m/%Y') > INTERVAL 41 DAYS
		THEN 'sim'
		ELSE 'não'
	END as 'Apto Tuberculose?',
	mt.idExameTub as 'Código Atestado Tuberculose',
	STRFTIME(mt.dtTub,'%d/%m/%Y') as 'Data Exame Tuberculose',
	rmt.ResTub as 'Resultado Tuberculose',
	COALESCE(rmt.dsTipoObservacao,obs.dsTipoobservacao,'') as 'Obs. Tuberculose'
	
	
	
FROM atRebanho rb
	LEFT JOIN max_bru mb on mb.nrBrinco = rb.nrBrinco
	LEFT JOIN atExameBrinco rmb on rmb.id_exame_pncebt = mb.idExameBru
		AND rb.nrBrinco = rmb.nrBrinco
	LEFT JOIN max_tub mt on mt.nrBrinco = rb.nrBrinco
	LEFT JOIN atExameBrinco rmt on rmt.id_exame_pncebt = mt.idExameTub
		AND rb.nrBrinco = rmt.nrBrinco
		LEFT JOIN max_obs mo on mo.nrBrinco = rb.nrBrinco
	LEFT JOIN atExameBrinco obs on obs.id_exame_pncebt = mo.idExameTub
		AND rb.nrBrinco = obs.nrBrinco
	
	


