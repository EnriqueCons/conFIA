DROP DATABASE IF EXISTS DB_conFIA;
CREATE DATABASE IF NOT EXISTS DB_conFIA;
USE DB_conFIA;

-- Tabla Usuario
CREATE TABLE Usuario (
    email VARCHAR(255) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    contrasena VARCHAR(1000) NOT NULL,
    tipo ENUM('Personal', 'Empresarial') NOT NULL,
    imagen VARCHAR(255) DEFAULT NULL
);

-- Tabla Personal
CREATE TABLE Personal (
    email VARCHAR(255) PRIMARY KEY,
    FOREIGN KEY (email) REFERENCES Usuario(email) ON DELETE CASCADE
);

-- Tabla Empresarial
CREATE TABLE Empresarial (
    email VARCHAR(255) PRIMARY KEY,
    direccion VARCHAR(255),
    descripcion TEXT,
    FOREIGN KEY (email) REFERENCES Usuario(email) ON DELETE CASCADE
);

-- Tabla Evento
CREATE TABLE Evento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    fechaHora DATETIME NOT NULL,
    aforoMax INT NOT NULL,
    tipoAcceso ENUM('QR', 'Reconocimiento Facial') NOT NULL,
    creadorEmail VARCHAR(255),
    ubicacion VARCHAR(255),
    imagen VARCHAR(255),
    FOREIGN KEY (creadorEmail) REFERENCES Empresarial(email) ON DELETE SET NULL
);

-- Tabla Inscripción
CREATE TABLE Inscripcion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_email VARCHAR(255),
    evento_id INT,
    foto VARCHAR(255), -- Ruta de la foto para reconocimiento facial
    qr VARCHAR(255),   -- Ruta del código QR generado
    data TEXT,         -- Información adicional (como encoding facial)
    FOREIGN KEY (usuario_email) REFERENCES Usuario(email),
    FOREIGN KEY (evento_id) REFERENCES Evento(id)
);

-- Tabla Certificado
CREATE TABLE Certificado (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    fechaGen DATE NOT NULL,
    url VARCHAR(255) NOT NULL,
    eventoId INT NOT NULL,
    usuarioEmail VARCHAR(255),
    FOREIGN KEY (eventoId) REFERENCES Evento(id) ON DELETE CASCADE,
    FOREIGN KEY (usuarioEmail) REFERENCES Personal(email) ON DELETE SET NULL
);

-- Tabla Documento
CREATE TABLE Documento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo ENUM('PDF', 'DOCX', 'Otros') NOT NULL,
    url VARCHAR(255) NOT NULL,
    eventoId INT NOT NULL,
    FOREIGN KEY (eventoId) REFERENCES Evento(id) ON DELETE CASCADE
);

-- Tabla Notificación
CREATE TABLE Notificacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mensaje TEXT NOT NULL,
    fechaEnvio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuarioEmail VARCHAR(255) NOT NULL,
    evento_id INT NULL,
    FOREIGN KEY (usuarioEmail) REFERENCES Usuario(email) ON DELETE CASCADE,
    FOREIGN KEY (evento_id) REFERENCES Evento(id) ON DELETE SET NULL
);


/*

-- Consultas de Prueba
select * from `Usuario`;
select * from `Personal`;
select * from `Empresarial`;
select * from `Evento`;

-- Insertar Usuario Personal
INSERT INTO Usuario (email, nombre, contrasena, tipo)
VALUES ('nahumfc@gmail.com', 'Nahum', 'contrausu1', 'Personal');

INSERT INTO Personal (email)
VALUES ('nahumfc@gmail.com');

                
-- Insertar Usuario Empresarial
INSERT INTO Usuario (email, nombre, contrasena, tipo)
VALUES ('oracle@gmail.com', 'Oracle', 'contra2', 'Empresarial');

INSERT INTO Empresarial (email, direccion, descripcion)
VALUES ('oracle@gmail.com', ' C. Montes Urales 470, Lomas - Virreyes, Lomas de Chapultepec, Miguel Hidalgo, 11000 Ciudad de México, CDMX', 'Nuestra misión es ayudar a las personas a ver los datos de nuevas maneras, descubrir ideas, desbloquear posibilidades sin fin.');

-- Insertar Evento creado por Usuario Empresarial
INSERT INTO Evento (nombre, descripcion, fechaHora, aforoMax, tipoAcceso, creadorEmail)
VALUES ('Conferencia de Tecnología', 'Evento sobre avances tecnológicos', '2024-12-01 10:00:00', 100, 'QR', 'oracle@gmail.com');



-- Insertar Inscripción de Usuario Personal a un Evento
INSERT INTO Inscripcion (estado, fechaInscripcion, usuarioEmail, eventoId)
VALUES ('Pendiente', '2024-11-20', 'personal@email.com', 1);

-- Insertar Documento relacionado con un Evento
INSERT INTO Documento (nombre, tipo, url, eventoId)
VALUES ('Agenda del Evento', 'PDF', 'https://ejemplo.com/agenda.pdf', 1);

-- Insertar Certificado generado para un Usuario Personal
INSERT INTO Certificado (nombre, fechaGen, url, eventoId, usuarioEmail)
VALUES ('Certificado de Asistencia', '2024-12-02', 'https://ejemplo.com/certificado.pdf', 1, 'personal@email.com');

-- Insertar Notificación para un Usuario
INSERT INTO Notificacion (mensaje, fechaEnvio, usuarioEmail)
VALUES ('Recordatorio: Asiste a la Conferencia de Tecnología mañana', '2024-11-30', 'personal@email.com');

-- Ver todos los usuarios
SELECT * FROM Usuario;

-- Ver usuarios personales
SELECT U.email, U.nombre
FROM Usuario U
JOIN Personal P ON U.email = P.email;

-- Ver usuarios empresariales
SELECT U.email, U.nombre, E.direccion, E.descripcion
FROM Usuario U
JOIN Empresarial E ON U.email = E.email;

-- Ver todos los eventos
SELECT * FROM Evento;

-- Ver eventos creados por un usuario empresarial específico
SELECT E.nombre, E.descripcion, E.fechaHora
FROM Evento E
WHERE E.creadorEmail = 'empresa@email.com';

-- Ver inscripciones por evento
SELECT I.estado, I.fechaInscripcion, U.nombre AS Usuario
FROM Inscripcion I
JOIN Personal P ON I.usuarioEmail = P.email
JOIN Usuario U ON P.email = U.email
WHERE I.eventoId = 1;

-- Ver certificados generados por evento
SELECT C.nombre, C.fechaGen, C.url, U.nombre AS Usuario
FROM Certificado C
JOIN Personal P ON C.usuarioEmail = P.email
JOIN Usuario U ON P.email = U.email
WHERE C.eventoId = 1;

-- Ver documentos asociados a un evento
SELECT D.nombre, D.tipo, D.url
FROM Documento D
WHERE D.eventoId = 1;

-- Ver notificaciones enviadas a un usuario
SELECT N.mensaje, N.fechaEnvio
FROM Notificacion N
WHERE N.usuarioEmail = 'personal@email.com';

*/