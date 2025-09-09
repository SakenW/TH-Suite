/**
 * 简单的压缩和解压缩工具
 * 使用浏览器内置的 CompressionStream API（如果可用）
 * 否则使用简单的字符串压缩算法
 */

export async function compress(data: string): Promise<string> {
  // 检查是否支持 CompressionStream
  if ('CompressionStream' in globalThis) {
    try {
      const encoder = new TextEncoder()
      const input = encoder.encode(data)

      const cs = new CompressionStream('gzip')
      const writer = cs.writable.getWriter()
      writer.write(input)
      writer.close()

      const output = []
      const reader = cs.readable.getReader()
      let result
      while (!(result = await reader.read()).done) {
        output.push(result.value)
      }

      const compressed = new Uint8Array(output.reduce((acc, chunk) => acc + chunk.length, 0))
      let offset = 0
      for (const chunk of output) {
        compressed.set(chunk, offset)
        offset += chunk.length
      }

      // 转换为 Base64
      return 'COMPRESSED:' + btoa(String.fromCharCode(...compressed))
    } catch (error) {
      console.warn('CompressionStream failed, using fallback:', error)
    }
  }

  // 降级方案：简单的 RLE 压缩
  return 'COMPRESSED:' + simpleCompress(data)
}

export async function decompress(data: string): Promise<string> {
  if (!data.startsWith('COMPRESSED:')) {
    return data
  }

  const compressed = data.substring('COMPRESSED:'.length)

  // 检查是否支持 DecompressionStream
  if ('DecompressionStream' in globalThis) {
    try {
      // 从 Base64 解码
      const binaryString = atob(compressed)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      const ds = new DecompressionStream('gzip')
      const writer = ds.writable.getWriter()
      writer.write(bytes)
      writer.close()

      const output = []
      const reader = ds.readable.getReader()
      let result
      while (!(result = await reader.read()).done) {
        output.push(result.value)
      }

      const decoder = new TextDecoder()
      return output.map(chunk => decoder.decode(chunk)).join('')
    } catch (error) {
      console.warn('DecompressionStream failed, using fallback:', error)
    }
  }

  // 降级方案：简单的 RLE 解压
  return simpleDecompress(compressed)
}

// 简单的游程编码压缩
function simpleCompress(str: string): string {
  let compressed = ''
  let count = 1

  for (let i = 0; i < str.length; i++) {
    if (str[i] === str[i + 1]) {
      count++
    } else {
      if (count > 3) {
        compressed += `${count}*${str[i]}`
      } else {
        compressed += str[i].repeat(count)
      }
      count = 1
    }
  }

  return compressed
}

// 简单的游程编码解压
function simpleDecompress(str: string): string {
  return str.replace(/(\d+)\*(.)/g, (match, count, char) => {
    return char.repeat(parseInt(count))
  })
}

// LZW 压缩算法（备选方案）
export function lzwCompress(str: string): string {
  const dict: { [key: string]: number } = {}
  const data = (str + '').split('')
  const out: number[] = []
  let currChar: string
  let phrase = data[0]
  let code = 256

  for (let i = 1; i < data.length; i++) {
    currChar = data[i]
    if (dict[phrase + currChar] != null) {
      phrase += currChar
    } else {
      out.push(phrase.length > 1 ? dict[phrase] : phrase.charCodeAt(0))
      dict[phrase + currChar] = code
      code++
      phrase = currChar
    }
  }

  out.push(phrase.length > 1 ? dict[phrase] : phrase.charCodeAt(0))

  return out.map(num => String.fromCharCode(num)).join('')
}

export function lzwDecompress(str: string): string {
  const dict: { [key: number]: string } = {}
  const data = (str + '').split('')
  let currChar = data[0]
  let oldPhrase = currChar
  const out = [currChar]
  let code = 256
  let phrase: string

  for (let i = 1; i < data.length; i++) {
    const currCode = data[i].charCodeAt(0)
    if (currCode < 256) {
      phrase = data[i]
    } else {
      phrase = dict[currCode] ? dict[currCode] : oldPhrase + currChar
    }
    out.push(phrase)
    currChar = phrase.charAt(0)
    dict[code] = oldPhrase + currChar
    code++
    oldPhrase = phrase
  }

  return out.join('')
}
